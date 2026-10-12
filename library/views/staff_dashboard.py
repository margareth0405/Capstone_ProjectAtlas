"""Administrator home, account-management, and reporting views."""

from django.views.generic import TemplateView

from library.models import LibraryItem, Profile, ResourceChangeRequest
from library.services import is_teacher
from library.services.staff_portal import StaffPortalContextService

from .mixins import PageContextMixin, ResourceManagerRequiredMixin, StaffRequiredMixin


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


class ResourceRequestsView(ResourceManagerRequiredMixin, PageContextMixin, TemplateView):
    """Show resource submissions and edit/delete decisions to the right role."""

    template_name = "library/resource_requests.html"
    active_page = "resource_requests"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        changes = ResourceChangeRequest.objects.select_related(
            "item", "requested_by", "reviewed_by"
        )
        submissions = LibraryItem.objects.select_related(
            "created_by", "reviewed_by"
        ).filter(created_by__profile__role=Profile.Role.TEACHER)
        if is_teacher(user):
            changes = changes.filter(requested_by=user)
            submissions = submissions.filter(created_by=user)
        context.update(
            {
                "resource_changes": changes.order_by("-created_at")[:100],
                "resource_submissions": submissions.order_by("-created_at")[:100],
                "staff_request_view": user.is_staff,
            }
        )
        return context
