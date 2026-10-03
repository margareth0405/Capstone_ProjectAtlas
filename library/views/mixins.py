"""Reusable view behavior for ATLAS class-based views."""

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.urls import reverse

from library.models import Profile
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


class ResourceManagerRequiredMixin:
    """Allow administrators and verified teacher-role accounts to manage resources."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), reverse("library:login"))
        profile = getattr(request.user, "profile", None)
        is_teacher = profile is not None and profile.role == Profile.Role.TEACHER
        if not (request.user.is_active and (request.user.is_staff or is_teacher)):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class SuperuserRequiredMixin:
    """Restrict especially sensitive staff actions to the root administrator."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), reverse("admin:login"))
        if not (
            request.user.is_active
            and request.user.is_staff
            and request.user.is_superuser
        ):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
