"""Catalog browsing, bookmarks, and privacy-safe resource reading."""

import logging
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from urllib.parse import urlencode

from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.http import content_disposition_header
from django.views import View
from django.views.generic import TemplateView
from PIL import Image, ImageOps, UnidentifiedImageError

from library.models import Favorite, LibraryItem, Profile, ResourceChangeRequest
from library.services import (
    CatalogQueryService,
    PageContextBuilder,
    SafeRedirectService,
    is_teacher,
    visible_library_items,
)
from library.services.documents import DocumentExtractionError, DocumentTextExtractor
from library.services.resource_views import ResourceViewTracker

from .mixins import PageContextMixin

logger = logging.getLogger(__name__)

STORAGE_READ_EXCEPTIONS = (BotoCoreError, ClientError, OSError)


class RegisteredResourceAccessMixin:
    """Send anonymous visitors to account creation before showing a resource."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            query = urlencode({"next": request.get_full_path()})
            return redirect(f"{reverse('library:register')}?{query}")
        return super().dispatch(request, *args, **kwargs)


REQUEST_FIELD_LABELS = {
    "collection": "Collection",
    "call_number": "Call number",
    "title": "Title",
    "author": "Author",
    "details": "Description or abstract",
    "file_type": "Resource abstract format",
    "pages": "Pages",
    "hard_copy_available": "Hard copy available",
    "published_on": "Publication date",
    "publication_day_known": "Exact publication day supplied",
    "cover_image": "Cover",
    "resource_abstract": "Resource abstract file",
}


def requested_change_rows(change):
    """Present only the fields identified by the teacher's edit request."""

    field_names = change.changed_fields or list(change.proposed_values)
    rows = []
    collection_labels = dict(LibraryItem.Collection.choices)
    file_type_labels = dict(LibraryItem.FileType.choices)
    for name in field_names:
        if name == "cover_image":
            value = "Remove the current cover" if change.clear_cover else "Use the uploaded replacement cover"
        elif name == "resource_abstract":
            value = "Use the uploaded replacement abstract"
        else:
            value = change.proposed_values.get(name)
            if name == "collection":
                value = collection_labels.get(value, value)
            elif name == "file_type":
                value = file_type_labels.get(value, value)
            elif isinstance(value, bool):
                value = "Yes" if value else "No"
            elif value in (None, ""):
                value = "Not specified"
        rows.append({"label": REQUEST_FIELD_LABELS.get(name, name), "value": value})
    return rows


class CatalogView(PageContextMixin, TemplateView):
    template_name = "library/catalog.html"
    active_page = "catalog"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query_service = CatalogQueryService(self.request.GET, user=self.request.user)
        items = query_service.build()
        favorite_ids = set()
        if self.request.user.is_authenticated and not self.request.user.is_staff:
            favorite_ids = set(
                Favorite.objects.filter(user=self.request.user).values_list(
                    "item_id", flat=True
                )
            )
        pending_change_ids = set()
        if self.request.user.is_authenticated and (
            self.request.user.is_staff or is_teacher(self.request.user)
        ):
            pending = ResourceChangeRequest.objects.filter(
                status=ResourceChangeRequest.Status.PENDING
            )
            if not self.request.user.is_staff:
                pending = pending.filter(requested_by=self.request.user)
            pending_change_ids = set(pending.values_list("item_id", flat=True))
        context.update(
            {
                "items": items,
                "library_items": items,
                "resources": items,
                "favorite_ids": favorite_ids,
                "query": query_service.query,
                "selected_collection": query_service.collection,
                "selected_sort": query_service.sort,
                "collection_choices": LibraryItem.Collection.choices,
                "pending_change_ids": pending_change_ids,
            }
        )
        return context


class ItemDetailView(RegisteredResourceAccessMixin, PageContextMixin, TemplateView):
    template_name = "library/item_detail.html"
    active_page = "catalog"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        item = get_object_or_404(
            visible_library_items(self.request.user).select_related(
                "created_by__profile", "reviewed_by"
            ),
            pk=self.kwargs["pk"],
        )
        context["item"] = item
        private_workflow_visible = self.request.user.is_authenticated and (
            self.request.user.is_staff or item.created_by_id == self.request.user.pk
        )
        latest_change = (
            item.change_requests.select_related("requested_by", "reviewed_by").first()
            if private_workflow_visible
            else None
        )
        context["latest_change"] = latest_change
        context["request_change_rows"] = (
            requested_change_rows(latest_change)
            if latest_change and latest_change.action == ResourceChangeRequest.Action.EDIT
            else []
        )
        creator_profile = getattr(item.created_by, "profile", None)
        context["show_submission_workflow"] = bool(
            private_workflow_visible
            and latest_change is None
            and creator_profile is not None
            and creator_profile.role == Profile.Role.TEACHER
        )
        context["has_pending_change"] = bool(
            latest_change and latest_change.status == ResourceChangeRequest.Status.PENDING
        )
        context["is_favorite"] = (
            self.request.user.is_authenticated
            and not self.request.user.is_staff
            and Favorite.objects.filter(user=self.request.user, item=item).exists()
        )
        return context


class ProtectedDocumentReaderView(
    RegisteredResourceAccessMixin, PageContextMixin, TemplateView
):
    """Base reader for extracting text without exposing an uploaded file."""

    template_name = "library/resource_abstract_reader.html"
    active_page = "catalog"
    extractor_class = DocumentTextExtractor
    tracker_class = ResourceViewTracker
    document_field = ""
    reader_heading = "Read document"
    reader_badge = "Protected document"
    missing_message = "This document is not available."

    def get(self, request, *args, **kwargs):
        """Keep protected reading responses out of browser and shared caches."""
        response = super().get(request, *args, **kwargs)
        response["Cache-Control"] = (
            "private, no-store, no-cache, must-revalidate, max-age=0"
        )
        response["Pragma"] = "no-cache"
        response["Expires"] = "0"
        response["X-Robots-Tag"] = "noindex, nofollow, noarchive"
        response["Cross-Origin-Resource-Policy"] = "same-origin"
        response["Permissions-Policy"] = (
            "clipboard-read=(), clipboard-write=(), display-capture=()"
        )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        item = get_object_or_404(
            visible_library_items(self.request.user), pk=self.kwargs["pk"]
        )
        document = getattr(item, self.document_field)
        content = ""
        reader_error = ""

        self.tracker_class().record(self.request, item)
        if not document:
            reader_error = self.missing_message
        else:
            try:
                document.open("rb")
                content = self.extractor_class().extract_for_reading(document)
            except DocumentExtractionError as exc:
                reader_error = str(exc)
            except STORAGE_READ_EXCEPTIONS:
                logger.exception(
                    "Stored %s is unavailable for repository item %s.",
                    self.document_field,
                    item.pk,
                )
                reader_error = (
                    "This stored document is temporarily unavailable. Please ask a "
                    "repository administrator to restore or replace the upload."
                )
            finally:
                try:
                    document.close()
                except STORAGE_READ_EXCEPTIONS:
                    logger.warning(
                        "Unable to close stored %s for repository item %s.",
                        self.document_field,
                        item.pk,
                        exc_info=True,
                    )

        context.update(
            {
                "item": item,
                "resource_content": content,
                "reader_error": reader_error,
                "reader_heading": self.reader_heading,
                "reader_badge": self.reader_badge,
                "document_display_type": self._document_display_type(document),
            }
        )
        return context

    @staticmethod
    def _document_display_type(document):
        extension = Path(document.name).suffix.lower() if document else ""
        return "Word document" if extension == ".docx" else "PDF"


class ResourceAbstractReaderView(ProtectedDocumentReaderView):
    """Show a resource abstract inside ATLAS without offering a download."""

    document_field = "resource_abstract"
    reader_heading = "Read resource abstract"
    reader_badge = "Protected resource abstract"
    missing_message = "This resource does not have a Resource abstract available."


class ResourceCoverView(View):
    """Serve a bounded WebP derivative while keeping MEDIA_ROOT private."""

    supported_extensions = frozenset({".jpg", ".jpeg", ".png", ".webp"})
    maximum_dimensions = (800, 1200)

    def get(self, request, pk):
        item = get_object_or_404(visible_library_items(request.user), pk=pk)
        cover = item.cover_image
        if not cover:
            raise Http404("Cover image not found.")
        extension = Path(cover.name).suffix.lower()
        if extension not in self.supported_extensions:
            raise Http404("Unsupported cover image.")
        fingerprint = sha256(cover.name.encode()).hexdigest()
        cache_key = f"atlas:cover:webp:{fingerprint}"
        optimized_bytes = cache.get(cache_key)
        if optimized_bytes is None:
            optimized_bytes = self._optimize(cover)
            cache.set(cache_key, optimized_bytes, timeout=86400)
        filename = f"{Path(cover.name).stem}.webp"
        response = HttpResponse(optimized_bytes, content_type="image/webp")
        response["Content-Disposition"] = content_disposition_header(False, filename)
        response["Cache-Control"] = "public, max-age=86400"
        response["X-Content-Type-Options"] = "nosniff"
        return response

    def _optimize(self, cover):
        try:
            cover.open("rb")
            with Image.open(cover) as source:
                image = ImageOps.exif_transpose(source)
                image.thumbnail(self.maximum_dimensions, Image.Resampling.LANCZOS)
                if image.mode not in {"RGB", "RGBA"}:
                    image = image.convert("RGBA" if "transparency" in image.info else "RGB")
                output = BytesIO()
                image.save(output, format="WEBP", quality=80, method=6)
        except (
            BotoCoreError,
            ClientError,
            Image.DecompressionBombError,
            OSError,
            UnidentifiedImageError,
            ValueError,
        ) as exc:
            logger.warning(
                "Cover image is unavailable for repository item %s.",
                cover.instance.pk,
                exc_info=True,
            )
            raise Http404("Cover image not found.") from exc
        finally:
            try:
                cover.close()
            except STORAGE_READ_EXCEPTIONS:
                logger.warning(
                    "Unable to close cover image for repository item %s.",
                    cover.instance.pk,
                    exc_info=True,
                )
        return output.getvalue()


class FavoritesView(PageContextMixin, TemplateView):
    template_name = "library/favorites.html"
    active_page = "favorites"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        if request.user.is_staff:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        links = Favorite.objects.filter(
            user=self.request.user,
            item__review_status=LibraryItem.ReviewStatus.APPROVED,
        ).select_related("item")
        context.update({"favorites": links, "items": [link.item for link in links]})
        return context


class FavoriteToggleView(View):
    def post(self, request, pk):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        if request.user.is_staff:
            raise PermissionDenied
        item = get_object_or_404(
            LibraryItem.objects.filter(
                review_status=LibraryItem.ReviewStatus.APPROVED
            ),
            pk=pk,
        )
        favorite, created = Favorite.objects.get_or_create(user=request.user, item=item)
        if created:
            message = f"Bookmarked {item.title}."
        else:
            favorite.delete()
            message = f"Removed the bookmark for {item.title}."
        cache.delete(PageContextBuilder.favorite_count_cache_key(request.user.pk))
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "bookmarked": created,
                    "item_id": item.pk,
                    "message": message,
                }
            )
        if created:
            messages.success(request, message)
        else:
            messages.info(request, message)
        return redirect(SafeRedirectService.resolve(request, "library:catalog"))
