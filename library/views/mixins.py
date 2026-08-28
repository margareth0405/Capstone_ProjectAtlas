"""Reusable view behavior for ATLAS class-based views."""

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.urls import reverse

from library.services import PageContextBuilder


class PageContextMixin:
    """Add ATLAS navigation and aggregate data to a template context."""

    active_page = "home"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(PageContextBuilder(self.request).build(self.active_page))
        return context


class StaffRequiredMixin:
    """Restrict a view to active Django staff accounts."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), reverse("admin:login"))
        if not (request.user.is_active and request.user.is_staff):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
