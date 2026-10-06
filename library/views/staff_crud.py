"""Administrator CRUD views for resources and announcements."""

import logging

from django.contrib import messages
from django.db import DatabaseError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from library.forms import AnnouncementForm, LibraryItemForm
from library.models import ActivityLog, Announcement, LibraryItem
from library.services import (
    PageContextBuilder,
    RepositoryItemPersistenceService,
    ResourceReviewAnalysisService,
    ResourceStorageError,
    is_teacher,
)
from library.services.activity import ActivityRecorder

from .mixins import ResourceManagerRequiredMixin, StaffRequiredMixin

logger = logging.getLogger(__name__)


class StaffFormView(View):
    """Shared create/edit workflow for staff-managed model forms."""

    form_class = None
    template_name = None
    active_page = "home"
    form_title = ""
    submit_label = "Save"
    success_message = "Saved."
    activity_object_type = "record"
    activity_recorder_class = ActivityRecorder

    def get_instance(self):
        return None

    def get_form(self):
        kwargs = {"instance": self.get_instance()}
        if self.request.method == "POST":
            kwargs["data"] = self.request.POST
            if self.form_class is LibraryItemForm:
                kwargs["files"] = self.request.FILES
        return self.form_class(**kwargs)

    def prepare_instance(self, instance):
        return instance

    def get_success_url(self, instance):
        if self.request.user.is_staff:
            return reverse("library:staff_portal")
        return reverse("library:catalog")

    def get(self, request, *args, **kwargs):
        return self.render_form(self.get_form())

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            is_create = form.instance.pk is None
            instance = self.save_form(form)
            self.activity_recorder_class.record(
                actor=request.user,
                action=(
                    ActivityLog.Action.CREATE
                    if is_create
                    else ActivityLog.Action.UPDATE
                ),
                object_type=self.activity_object_type,
                object_id=instance.pk,
                description=str(instance),
            )
            messages.success(request, self.success_message)
            return redirect(self.get_success_url(instance))
        messages.error(
            request,
            "The record was not saved. Review the highlighted fields.",
        )
        return self.render_form(form)

    def save_form(self, form):
        instance = self.prepare_instance(form.save(commit=False))
        instance.save()
        form.save_m2m()
        return instance

    def render_form(self, form):
        context = PageContextBuilder(self.request).build(self.active_page)
        context.update(
            {
                "form": form,
                "form_title": self.form_title,
                "submit_label": self.submit_label,
            }
        )
        return render(self.request, self.template_name, context)


class StaffItemCreateView(ResourceManagerRequiredMixin, StaffFormView):
    """Create one Digital Sources resource."""

    form_class = LibraryItemForm
    template_name = "library/admin/item_form.html"
    active_page = "catalog"
    form_title = "Add Digital Sources item"
    submit_label = "Add item"
    activity_object_type = "repository resource"
    persistence_service_class = RepositoryItemPersistenceService
    review_service_class = ResourceReviewAnalysisService

    def get_success_url(self, instance):
        """Keep resource management on the dedicated Digital Sources page."""

        return reverse("library:catalog")

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ResourceStorageError:
            form = self.get_form()
            form.add_error(
                None,
                "The resource could not be uploaded to storage. Check the "
                "connection and storage settings, then choose the file and try again.",
            )
            messages.error(
                request,
                "The resource upload did not finish. No repository record was created.",
            )
            return self.render_form(form)

    def save_form(self, form):
        instance = self.persistence_service_class().save(
            form,
            prepare_instance=self.prepare_instance,
        )
        if is_teacher(self.request.user):
            analysis_completed = self.review_service_class().analyze(
                instance,
                reviewer=self.request.user,
            )
            if analysis_completed:
                self.success_message = (
                    f"{instance.title} completed AI analysis and is pending "
                    "Administrator review."
                )
            else:
                self.success_message = (
                    f"{instance.title} is pending Administrator review. "
                    "Automatic analysis needs a manual check."
                )
        return instance

    def prepare_instance(self, instance):
        instance.created_by = self.request.user
        if is_teacher(self.request.user):
            instance.review_status = LibraryItem.ReviewStatus.PENDING
            instance.ai_review_status = LibraryItem.AIReviewStatus.NOT_RUN
            instance.ai_review_summary = {}
            instance.reviewed_by = None
            instance.reviewed_at = None
            instance.review_notes = ""
        else:
            instance.review_status = LibraryItem.ReviewStatus.APPROVED
        self.success_message = f"{instance.title} was added to Digital Sources."
        return instance


class StaffItemEditView(StaffItemCreateView):
    """Edit one existing Digital Sources resource."""

    form_title = "Edit Digital Sources item"
    submit_label = "Save changes"

    def get_instance(self):
        return get_object_or_404(LibraryItem, pk=self.kwargs["pk"])

    def prepare_instance(self, instance):
        if is_teacher(self.request.user):
            instance.created_by = self.request.user
            instance.review_status = LibraryItem.ReviewStatus.PENDING
            instance.ai_review_status = LibraryItem.AIReviewStatus.NOT_RUN
            instance.ai_review_summary = {}
            instance.reviewed_by = None
            instance.reviewed_at = None
            instance.review_notes = ""
        self.success_message = f"{instance.title} was updated."
        return instance


class StaffItemReviewView(StaffRequiredMixin, View):
    """Present a teacher submission and its automatic screening to staff."""

    template_name = "library/admin/item_review.html"

    def get(self, request, pk):
        item = get_object_or_404(LibraryItem, pk=pk)
        context = PageContextBuilder(request).build("catalog")
        context["item"] = item
        return render(request, self.template_name, context)


class StaffItemReviewDecisionView(StaffRequiredMixin, View):
    """Record a staff decision and control public repository publication."""

    review_status = None
    decision_label = "updated"
    activity_recorder_class = ActivityRecorder

    def post(self, request, pk):
        item = get_object_or_404(LibraryItem, pk=pk)
        try:
            with transaction.atomic():
                item.review_status = self.review_status
                item.reviewed_by = request.user
                item.reviewed_at = timezone.now()
                item.review_notes = request.POST.get("review_notes", "").strip()[:2000]
                item.save(
                    update_fields=(
                        "review_status",
                        "reviewed_by",
                        "reviewed_at",
                        "review_notes",
                        "updated_at",
                    )
                )
                self.activity_recorder_class.record(
                    actor=request.user,
                    action=ActivityLog.Action.UPDATE,
                    object_type="repository resource review",
                    object_id=item.pk,
                    description=f"{item.title}: {item.get_review_status_display()}",
                )
        except DatabaseError:
            logger.exception("Repository review decision failed for item %s", item.pk)
            messages.error(
                request,
                "The review decision could not be saved. No publication status changed.",
            )
            return redirect("library:staff_item_review", pk=item.pk)
        messages.success(request, f"{item.title} was {self.decision_label}.")
        return redirect("library:staff_item_review", pk=item.pk)


class StaffItemApproveView(StaffItemReviewDecisionView):
    review_status = LibraryItem.ReviewStatus.APPROVED
    decision_label = "approved and published"


class StaffItemRejectView(StaffItemReviewDecisionView):
    review_status = LibraryItem.ReviewStatus.REJECTED
    decision_label = "returned to the teacher for changes"


class StaffItemDeleteView(ResourceManagerRequiredMixin, View):
    """Delete one Digital Sources resource and retain an audit entry."""

    activity_recorder_class = ActivityRecorder
    persistence_service_class = RepositoryItemPersistenceService

    def post(self, request, pk):
        item = get_object_or_404(LibraryItem, pk=pk)
        title = item.title
        self.persistence_service_class().delete(item)
        self.activity_recorder_class.record(
            actor=request.user,
            action=ActivityLog.Action.DELETE,
            object_type="repository resource",
            object_id=pk,
            description=title,
        )
        messages.info(request, f"{title} was removed from Digital Sources.")
        return redirect("library:catalog")


class StaffAnnouncementCreateView(StaffRequiredMixin, StaffFormView):
    """Create and optionally publish one announcement."""

    form_class = AnnouncementForm
    template_name = "library/admin/announcement_form.html"
    active_page = "announcements"
    form_title = "Create announcement"
    submit_label = "Save announcement"
    activity_object_type = "announcement"

    def prepare_instance(self, instance):
        instance.created_by = self.request.user
        instance.is_featured = False
        instance.is_published = False
        instance.published_at = None
        self.success_message = "Announcement saved as a draft. Review it, then select Publish."
        return instance

    def get_success_url(self, instance):
        return f'{reverse("library:announcements")}#announcement-{instance.pk}'


class StaffAnnouncementEditView(StaffAnnouncementCreateView):
    """Edit one existing announcement."""

    form_title = "Edit announcement"
    submit_label = "Save changes"

    def get_instance(self):
        return get_object_or_404(Announcement, pk=self.kwargs["pk"])

    def prepare_instance(self, instance):
        instance.is_featured = False
        self.success_message = (
            "Published announcement updated."
            if instance.is_published
            else "Draft announcement updated. Select Publish when it is ready."
        )
        return instance


class StaffAnnouncementPublishView(StaffRequiredMixin, View):
    """Publish a reviewed draft so it becomes visible to every reader role."""

    activity_recorder_class = ActivityRecorder

    def post(self, request, pk):
        announcement = get_object_or_404(Announcement, pk=pk)
        announcement.is_featured = False
        announcement.is_published = True
        announcement.published_at = timezone.now()
        announcement.save(
            update_fields=("is_featured", "is_published", "published_at", "updated_at")
        )
        self.activity_recorder_class.record(
            actor=request.user,
            action=ActivityLog.Action.UPDATE,
            object_type="announcement",
            object_id=announcement.pk,
            description=f"Published: {announcement.title}",
        )
        messages.success(request, f"{announcement.title} is now published.")
        return redirect(f'{reverse("library:announcements")}#announcement-{announcement.pk}')


class StaffAnnouncementUnpublishView(StaffRequiredMixin, View):
    """Return an announcement to draft status."""

    activity_recorder_class = ActivityRecorder

    def post(self, request, pk):
        announcement = get_object_or_404(Announcement, pk=pk)
        announcement.is_published = False
        announcement.published_at = None
        announcement.save(update_fields=("is_published", "published_at", "updated_at"))
        self.activity_recorder_class.record(
            actor=request.user,
            action=ActivityLog.Action.UPDATE,
            object_type="announcement",
            object_id=announcement.pk,
            description=f"Unpublished: {announcement.title}",
        )
        messages.info(request, f"{announcement.title} is now a draft.")
        return redirect(f'{reverse("library:announcements")}#announcement-{announcement.pk}')


class StaffAnnouncementDeleteView(StaffRequiredMixin, View):
    """Delete one announcement and retain an audit entry."""

    activity_recorder_class = ActivityRecorder

    def post(self, request, pk):
        announcement = get_object_or_404(Announcement, pk=pk)
        title = announcement.title
        announcement.delete()
        self.activity_recorder_class.record(
            actor=request.user,
            action=ActivityLog.Action.DELETE,
            object_type="announcement",
            object_id=pk,
            description=title,
        )
        messages.info(request, f"{title} was deleted.")
        return redirect("library:announcements")
