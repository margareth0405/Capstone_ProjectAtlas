"""Catalog browsing, favorites, and download views."""

from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import TemplateView

from library.models import DownloadEvent, Favorite, LibraryItem
from library.services import CatalogQueryService, SafeRedirectService

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
        for item in items:
            item.is_favorite = item.pk in favorite_ids
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
            messages.success(request, f"Added {item.title} to your favorites.")
        else:
            favorite.delete()
            messages.info(request, f"Removed {item.title} from your favorites.")
        return redirect(SafeRedirectService.resolve(request, "library:catalog"))


class DownloadView(View):
    def get(self, request, pk):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        item = get_object_or_404(LibraryItem, pk=pk)
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ip_address = (
            forwarded.split(",")[0].strip()
            if forwarded
            else request.META.get("REMOTE_ADDR")
        )
        DownloadEvent.objects.create(
            user=request.user,
            item=item,
            ip_address=ip_address or None,
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
        )
        if item.resource:
            return FileResponse(
                item.resource.open("rb"),
                as_attachment=True,
                filename=Path(item.resource.name).name,
            )
        if item.external_url:
            return redirect(item.external_url)
        messages.warning(
            request, "This catalog record does not have a file attached yet."
        )
        return redirect("library:item_detail", pk=item.pk)
