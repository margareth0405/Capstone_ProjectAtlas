"""Catalog browsing, bookmarks, and privacy-safe resource reading."""

from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from library.models import Announcement, Favorite, LibraryItem
from library.services import CatalogQueryService, SafeRedirectService
from library.services.documents import DocumentExtractionError, DocumentTextExtractor
from library.services.resource_views import ResourceViewTracker

from .mixins import PageContextMixin


class CatalogView(PageContextMixin, TemplateView):
    template_name = "library/catalog.html"
    active_page = "catalog"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query_service = CatalogQueryService(self.request.GET)
        items = query_service.build()
        favorite_ids = set()
        if self.request.user.is_authenticated and not self.request.user.is_staff:
            favorite_ids = set(
                Favorite.objects.filter(user=self.request.user).values_list(
                    "item_id", flat=True
                )
            )
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
                "recent_announcements": Announcement.objects.filter(
                    is_published=True,
                    published_at__lte=timezone.now(),
                )[:3],
            }
        )
        return context


class ItemDetailView(PageContextMixin, TemplateView):
    template_name = "library/item_detail.html"
    active_page = "catalog"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        item = get_object_or_404(LibraryItem, pk=self.kwargs["pk"])
        context["item"] = item
        context["is_favorite"] = (
            self.request.user.is_authenticated
            and not self.request.user.is_staff
            and Favorite.objects.filter(user=self.request.user, item=item).exists()
        )
        return context


class ProtectedDocumentReaderView(PageContextMixin, TemplateView):
    """Base reader for extracting text without exposing an uploaded file."""

    template_name = "library/resource_abstract_reader.html"
    active_page = "catalog"
    extractor_class = DocumentTextExtractor
    tracker_class = ResourceViewTracker
    document_field = ""
    reader_heading = "Read document"
    reader_badge = "Protected document"
    missing_message = "This document is not available."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        item = get_object_or_404(LibraryItem, pk=self.kwargs["pk"])
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
            except (DocumentExtractionError, OSError) as exc:
                reader_error = str(exc)
            finally:
                document.close()

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
    """Serve a validated cover inline while keeping MEDIA_ROOT private."""

    content_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }

    def get(self, request, pk):
        item = get_object_or_404(LibraryItem, pk=pk)
        cover = item.cover_image
        if not cover:
            raise Http404("Cover image not found.")
        extension = Path(cover.name).suffix.lower()
        content_type = self.content_types.get(extension)
        if not content_type:
            raise Http404("Unsupported cover image.")
        try:
            cover.open("rb")
        except OSError as exc:
            raise Http404("Cover image not found.") from exc
        response = FileResponse(
            cover,
            as_attachment=False,
            filename=Path(cover.name).name,
            content_type=content_type,
        )
        response["Cache-Control"] = "private, max-age=3600"
        response["X-Content-Type-Options"] = "nosniff"
        return response


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
        links = Favorite.objects.filter(user=self.request.user).select_related("item")
        context.update({"favorites": links, "items": [link.item for link in links]})
        return context


class FavoriteToggleView(View):
    def post(self, request, pk):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        if request.user.is_staff:
            raise PermissionDenied
        item = get_object_or_404(LibraryItem, pk=pk)
        favorite, created = Favorite.objects.get_or_create(user=request.user, item=item)
        if created:
            messages.success(request, f"Bookmarked {item.title}.")
        else:
            favorite.delete()
            messages.info(request, f"Removed the bookmark for {item.title}.")
        return redirect(SafeRedirectService.resolve(request, "library:catalog"))
