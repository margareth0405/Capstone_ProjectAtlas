"""Dashboard, announcements, contact, and machine-readable public views."""

import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.contrib.sites.requests import RequestSite
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from library.forms import ContactForm
from library.models import Announcement, ContactMessage, LibraryItem
from library.services.contact import ContactEmailService
from library.services.deployment import HealthCheckService
from library.sitemaps import sitemaps

from .mixins import PageContextMixin

logger = logging.getLogger(__name__)


class HealthCheckView(View):
    """Provide a safe load-balancer readiness endpoint."""

    service_class = HealthCheckService

    def get(self, request):
        report, healthy = self.service_class().check()
        response = JsonResponse(report, status=200 if healthy else 503)
        response["Cache-Control"] = "no-store"
        return response


class RobotsView(View):
    def get(self, request):
        sitemap_url = request.build_absolute_uri(reverse("library:sitemap"))
        return HttpResponse(
            "\n".join(
                (
                    "User-agent: *",
                    "Allow: /",
                    "Disallow: /staff/",
                    "Disallow: /accounts/",
                    "Disallow: /login/",
                    "Disallow: /register/",
                    "Disallow: /guest/",
                    "Disallow: /usage/",
                    "Disallow: /health/",
                    f"Sitemap: {sitemap_url}",
                    "",
                )
            ),
            content_type="text/plain; charset=utf-8",
        )


class SitemapView(View):
    """Generate public URLs from the current host, not a stale Site row."""

    def get(self, request):
        current_site = RequestSite(request)
        urls = []
        for sitemap_class in sitemaps.values():
            urls.extend(sitemap_class().get_urls(site=current_site))
        response = TemplateResponse(
            request,
            "sitemap.xml",
            {"urlset": urls},
            content_type="application/xml",
        )
        response["X-Robots-Tag"] = "noindex, noodp, noarchive"
        return response


class PrivacyTermsView(TemplateView):
    template_name = "library/privacy_terms.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "support_email": settings.SUPPORT_EMAIL,
                "data_privacy_email": settings.DATA_PRIVACY_EMAIL,
                "business_name": settings.BUSINESS_NAME,
                "business_operator": settings.BUSINESS_OPERATOR,
                "business_service_type": settings.BUSINESS_SERVICE_TYPE,
                "business_country": settings.BUSINESS_COUNTRY,
                "business_address": settings.BUSINESS_ADDRESS,
                "support_hours": settings.SUPPORT_HOURS,
                "support_phone": settings.SUPPORT_PHONE,
            }
        )
        return context


class UsageHeartbeatView(View):
    """Receive visible-page activity and deduplicated navigation events."""

    allowed_events = {"page_view", "heartbeat"}

    def post(self, request):
        if not (
            request.user.is_authenticated or request.session.get("guest_mode")
        ):
            return HttpResponse(status=403)

        if request.COOKIES.get("atlas_cookie_consent") != "analytics":
            return HttpResponse(status=204)

        event = request.POST.get("event", "")
        if event not in self.allowed_events:
            return HttpResponse(status=400)
        request.atlas_usage_event = event

        if event == "page_view":
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
        published_announcements = Announcement.objects.filter(
            is_published=True,
            published_at__lte=timezone.now(),
        )
        announcements = (
            Announcement.objects.all()
            if self.request.user.is_authenticated and self.request.user.is_staff
            else published_announcements
        )
        category = self.request.GET.get("category", "").strip()
        valid_categories = {value for value, _label in Announcement.Category.choices}
        if category in valid_categories:
            announcements = announcements.filter(category=category)
        context.update(
            {
                "announcements": announcements,
                "announcement_count": announcements.count(),
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
        request_type = self.request.GET.get(
            "request_type", ContactMessage.RequestType.SUPPORT
        )
        valid_request_types = {
            value for value, _label in ContactMessage.RequestType.choices
        }
        if request_type not in valid_request_types:
            request_type = ContactMessage.RequestType.SUPPORT
        initial = {"request_type": request_type}
        if self.request.user.is_authenticated:
            initial.update(
                {
                    "name": self.request.user.get_full_name(),
                    "email": self.request.user.email,
                }
            )
        return initial

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
                messages.error(
                    request,
                    "Your message could not be sent. Use the support email shown on this page.",
                )
            else:
                contact_message.save()
                success_message = (
                    "Your data deletion request has been submitted for review. "
                    "The repository team may contact you to verify your identity."
                    if contact_message.request_type
                    == ContactMessage.RequestType.DATA_DELETION
                    else f"Your message has been sent to {settings.SUPPORT_EMAIL}."
                )
                messages.success(
                    request,
                    success_message,
                )
                return redirect("library:contact")
        else:
            messages.error(
                request,
                "Your message was not sent. Review the highlighted fields.",
            )
        return self.render_to_response(self.get_context_data(form=form))
