"""Administrator homepage view."""

from django.views.generic import TemplateView

from library.forms import AdminCreatedUserForm, AnnouncementForm, LibraryItemForm
from library.services.staff_portal import StaffPortalContextService

from .mixins import PageContextMixin, StaffRequiredMixin


class StaffPortalView(StaffRequiredMixin, PageContextMixin, TemplateView):
    """Render administrator summaries, management tables, and usage analytics."""

    template_name = "library/staff_portal.html"
    context_service_class = StaffPortalContextService

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        portal_context = self.context_service_class(self.request).build()
        context["stats"].update(portal_context.pop("staff_stats"))
        context.update(portal_context)
        context.update(
            {
                "item_form": LibraryItemForm(),
                "announcement_form": AnnouncementForm(),
                "user_form": AdminCreatedUserForm(),
            }
        )
        return context
