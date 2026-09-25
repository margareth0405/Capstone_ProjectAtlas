"""Catalog browsing, bookmarks, and privacy-safe resource reading."""

import logging
from hashlib import sha256
from io import BytesIO
from pathlib import Path

from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.utils.http import content_disposition_header
from django.views import View
from django.views.generic import TemplateView
from PIL import Image, ImageOps, UnidentifiedImageError

from library.models import Announcement, Favorite, LibraryItem
from library.services import CatalogQueryService, SafeRedirectService
from library.services.documents import DocumentExtractionError, DocumentTextExtractor
from library.services.resource_views import ResourceViewTracker

from .mixins import PageContextMixin

logger = logging.getLogger(__name__)

STORAGE_READ_EXCEPTIONS = (BotoCoreError, ClientError, OSError)


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
        item = get_object_or_404(LibraryItem, pk=pk)
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
            message = f"Bookmarked {item.title}."
        else:
            favorite.delete()
            message = f"Removed the bookmark for {item.title}."
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
