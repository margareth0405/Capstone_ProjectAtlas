"""Administrator home, account-management, and reporting views."""

from django.views.generic import TemplateView

from library.models import LibraryItem, ResourceChangeRequest
from library.services.staff_portal import StaffPortalContextService

from .mixins import PageContextMixin, StaffRequiredMixin


class StaffPortalBaseView(StaffRequiredMixin, PageContextMixin, TemplateView):
    """Build the shared administrator data used by focused staff pages."""

    context_service_class = StaffPortalContextService
    portal_section = "home"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        portal_context = self.context_service_class(self.request).build()
        context["stats"].update(portal_context.pop("staff_stats"))
        context.update(portal_context)
        context["portal_section"] = self.portal_section
        return context


class StaffPortalView(StaffPortalBaseView):
    """Render a compact administrator home page."""

    template_name = "library/staff_home.html"
    active_page = "home"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pending_additions"] = LibraryItem.objects.filter(
            review_status=LibraryItem.ReviewStatus.PENDING
        ).select_related("created_by").order_by("-created_at")[:8]
        context["pending_changes"] = ResourceChangeRequest.objects.filter(
            status=ResourceChangeRequest.Status.PENDING
        ).select_related("item", "requested_by").order_by("-created_at")[:8]
        return context


class StaffUsersView(StaffPortalBaseView):
    """Render account management on its own page."""

    template_name = "library/staff_portal.html"
    active_page = "users"
    portal_section = "users"


class StaffReportsView(StaffPortalBaseView):
    """Render privacy-conscious usage and audit reporting separately."""

    template_name = "library/staff_portal.html"
    active_page = "reports"
    portal_section = "reports"
