"""Dashboard, announcements, contact, and machine-readable public views."""

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

from .mixins import PageContextMixin


class RobotsView(View):
    def get(self, request):
        return HttpResponse(
            "User-agent: *\nDisallow: /staff/\n", content_type="text/plain"
        )


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
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        form = ContactForm(request.POST, initial=self.get_initial())
        if form.is_valid():
            contact_message = form.save(commit=False)
            if request.user.is_authenticated:
                contact_message.user = request.user
            contact_message.save()
            messages.success(request, "Your message has been sent to the ATLAS team.")
            return redirect("library:contact")
        return self.render_to_response(self.get_context_data(form=form))
