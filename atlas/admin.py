"""ATLAS-specific Django administration site behavior."""

from django.contrib.admin import AdminSite
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.views import LoginView
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache


class AtlasAdminSite(AdminSite):
    """Keep Django's model tools while using ATLAS as the staff landing page."""

    site_header = "ATLAS Administration"
    site_title = "ATLAS Admin"
    index_title = "Digital Sources management"

    def index(self, request, extra_context=None):
        """Send staff away from Django's stock index to the custom workspace."""

        return HttpResponseRedirect(reverse("library:staff_portal"))

    @method_decorator(never_cache)
    @login_not_required
    def login(self, request, extra_context=None):
        """Use the custom staff workspace as the default post-login destination."""

        staff_portal_url = reverse("library:staff_portal")
        if request.method == "GET" and self.has_permission(request):
            return HttpResponseRedirect(staff_portal_url)

        # This mirrors Django's AdminSite.login context while changing only its
        # default destination. Explicit, safe ``next`` values continue to work.
        context = {
            **self.each_context(request),
            "title": _("Log in"),
            "subtitle": None,
            "app_path": request.get_full_path(),
            "username": request.user.get_username(),
        }
        if (
            REDIRECT_FIELD_NAME not in request.GET
            and REDIRECT_FIELD_NAME not in request.POST
        ):
            context[REDIRECT_FIELD_NAME] = staff_portal_url
        context.update(extra_context or {})

        defaults = {
            "extra_context": context,
            "authentication_form": self.login_form,
            "template_name": self.login_template or "admin/login.html",
            "next_page": staff_portal_url,
        }
        request.current_app = self.name
        return LoginView.as_view(**defaults)(request)
