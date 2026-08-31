"""Dashboard, announcements, contact, and machine-readable public views."""

import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from library.forms import ContactForm
from library.models import Announcement, LibraryItem
from library.services.contact import ContactEmailService

from .mixins import PageContextMixin

logger = logging.getLogger(__name__)


class RobotsView(View):
    def get(self, request):
        return HttpResponse(
            "User-agent: *\nDisallow: /staff/\n", content_type="text/plain"
        )


class UsageHeartbeatView(View):
    """Receive active-time heartbeats and reload-aware page-view events."""

    def post(self, request):
        if not (
            request.user.is_authenticated or request.session.get("guest_mode")
        ):
            return HttpResponse(status=403)

        if request.POST.get("event") == "page_view":
            page_path = request.POST.get("path", "").strip()
            if not page_path.startswith("/") or page_path.startswith("//"):
                return HttpResponse(status=400)
            request.atlas_usage_page_path = page_path[:255]

        return HttpResponse(status=204)

class DashboardView(PageContextMixin, TemplateView):
    template_name = "library/dashboard.html"
    active_page = "home"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated and not request.session.get("guest_mode"):
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        recent_items = LibraryItem.objects.order_by("-created_at")[:6]
        context.update(
            {
                "recent_items": recent_items,
                "recent_list": recent_items,
                "recent_announcements": Announcement.objects.filter(
                    is_published=True,
                    published_at__lte=timezone.now(),
                )[:3],
            }
        )
        return context


class AnnouncementsView(PageContextMixin, TemplateView):
    template_name = "library/announcements.html"
    active_page = "announcements"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        announcements = Announcement.objects.filter(
            is_published=True,
            published_at__lte=timezone.now(),
        )
        category = self.request.GET.get("category", "").strip()
        valid_categories = {value for value, _label in Announcement.Category.choices}
        if category in valid_categories:
            announcements = announcements.filter(category=category)
        context.update(
            {
                "announcements": announcements,
                "announcement_count": announcements.count(),
                "featured_announcement": announcements.filter(is_featured=True).first(),
                "selected_category": category,
                "category_choices": Announcement.Category.choices,
            }
        )
        return context


class ContactView(PageContextMixin, TemplateView):
    template_name = "library/contact.html"
    active_page = "contact"
    email_service_class = ContactEmailService

    def get_initial(self):
        if self.request.user.is_authenticated:
            return {
                "name": self.request.user.get_full_name(),
                "email": self.request.user.email,
            }
        return {}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("form", ContactForm(initial=self.get_initial()))
        context.update(
            {
                "contact_name": self.request.user.get_full_name()
                if self.request.user.is_authenticated
                else "",
                "contact_email": self.request.user.email
                if self.request.user.is_authenticated
                else "",
                "support_email": settings.SUPPORT_EMAIL,
                "support_hours": settings.SUPPORT_HOURS,
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        form = ContactForm(request.POST, initial=self.get_initial())
        if form.is_valid():
            contact_message = form.save(commit=False)
            if request.user.is_authenticated:
                contact_message.user = request.user

            account_email = (
                request.user.email if request.user.is_authenticated else "Guest visitor"
            )
            email_service = self.email_service_class()
            try:
                email_service.deliver(
                    contact_message,
                    account_email=account_email,
                )
            except Exception:
                logger.exception("Unable to deliver an ATLAS contact message.")
                form.add_error(
                    None,
                    "We could not send your message right now. Please email "
                    f"{settings.SUPPORT_EMAIL} directly.",
                )
            else:
                contact_message.save()
                messages.success(
                    request,
                    f"Your message has been sent to {settings.SUPPORT_EMAIL}.",
                )
                return redirect("library:contact")
        return self.render_to_response(self.get_context_data(form=form))
