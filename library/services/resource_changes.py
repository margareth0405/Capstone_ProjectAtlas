"""Stage teacher resource changes and apply them only after staff approval."""

from django.db import transaction
from django.utils import timezone

from library.models import LibraryItem, ResourceChangeRequest

from .repository_items import RepositoryItemPersistenceService, ResourceStorageError


PROPOSED_FIELDS = (
    "collection", "call_number", "title", "author", "details", "file_type",
    "pages", "hard_copy_available", "published_on", "publication_day_known",
)


class ResourceChangeService:
    persistence_service_class = RepositoryItemPersistenceService

    def submit_edit(self, *, form, item, requester):
        proposal = form.save(commit=False)
        values = {
            name: (
                getattr(proposal, name).isoformat()
                if name == "published_on" and getattr(proposal, name)
                else getattr(proposal, name)
            )
            for name in PROPOSED_FIELDS
        }
        changed_fields = {
            name
            for name in form.changed_data
            if name in PROPOSED_FIELDS or name in {"cover_image", "resource_abstract"}
        }
        if {"publication_month", "publication_day"} & set(form.changed_data):
            changed_fields.update({"published_on", "publication_day_known"})
        request = ResourceChangeRequest(
            item=item, requested_by=requester,
            action=ResourceChangeRequest.Action.EDIT,
            item_title=item.title,
            item_call_number=item.call_number,
            proposed_values=values,
            changed_fields=sorted(changed_fields),
            request_notes=form.cleaned_data.get("review_message", "").strip(),
            clear_cover=(
                "cover_image" in form.changed_data
                and form.cleaned_data.get("cover_image") is False
            ),
        )
        new_files = []
        try:
            with transaction.atomic():
                if "cover_image" in form.changed_data and form.cleaned_data.get("cover_image") not in (None, False):
                    request.cover_upload = form.cleaned_data["cover_image"]
                    new_files.append("cover_upload")
                if "resource_abstract" in form.changed_data and form.cleaned_data.get("resource_abstract"):
                    request.abstract_upload = form.cleaned_data["resource_abstract"]
                    new_files.append("abstract_upload")
                request.save()
                for name in new_files:
                    stored = getattr(request, name)
                    if not stored.storage.exists(stored.name):
                        raise ResourceStorageError("The proposed upload could not be verified.")
        except Exception as exc:
            for name in new_files:
                stored = getattr(request, name)
                if stored and stored._committed:
                    self.persistence_service_class._safe_delete(
                        stored.storage, stored.name
                    )
            if isinstance(exc, self.persistence_service_class.storage_exceptions):
                raise ResourceStorageError("The proposed upload could not be stored.") from exc
            raise
        return request

    def submit_delete(self, *, item, requester, request_notes=""):
        return ResourceChangeRequest.objects.create(
            item=item, requested_by=requester,
            action=ResourceChangeRequest.Action.DELETE,
            item_title=item.title,
            item_call_number=item.call_number,
            request_notes=request_notes.strip()[:2000],
        )

    def decide(self, *, change, reviewer, approve, notes):
        old_files = {}
        persistence = self.persistence_service_class()
        with transaction.atomic():
            change = ResourceChangeRequest.objects.select_for_update().get(pk=change.pk)
            if change.status != ResourceChangeRequest.Status.PENDING:
                return None
            item = LibraryItem.objects.select_for_update().get(pk=change.item_id)
            if approve and change.action == ResourceChangeRequest.Action.EDIT:
                old_files = persistence._file_snapshots(item)
                for name, value in change.proposed_values.items():
                    setattr(item, name, value)
                if change.clear_cover:
                    item.cover_image = ""
                elif change.cover_upload:
                    item.cover_image = change.cover_upload.name
                if change.abstract_upload:
                    item.resource_abstract = change.abstract_upload.name
                item.save()
            change.status = (
                ResourceChangeRequest.Status.APPROVED
                if approve else ResourceChangeRequest.Status.REJECTED
            )
            change.reviewed_by = reviewer
            change.reviewed_at = timezone.now()
            change.review_notes = notes
            change.save(update_fields=(
                "status", "reviewed_by", "reviewed_at", "review_notes"
            ))
            if approve and change.action == ResourceChangeRequest.Action.DELETE:
                old_files = persistence._file_snapshots(item)
                item.delete()
                change.item_id = None
        if approve and change.action == ResourceChangeRequest.Action.DELETE:
            for storage, name in old_files.values():
                persistence._safe_delete(storage, name)
        elif approve and change.action == ResourceChangeRequest.Action.EDIT:
            persistence._remove_replaced_files(item, old_files)
        elif not approve:
            for name in ("cover_upload", "abstract_upload"):
                stored = getattr(change, name)
                if stored:
                    persistence._safe_delete(stored.storage, stored.name)
            ResourceChangeRequest.objects.filter(pk=change.pk).update(
                cover_upload="", abstract_upload=""
            )
        return change
