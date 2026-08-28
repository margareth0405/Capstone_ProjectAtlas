"""Authentication and session views."""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from allauth.account import app_settings as allauth_account_settings
from allauth.account.utils import complete_signup, perform_login, setup_user_email

from library.forms import RegistrationForm, RoleLoginForm
from library.models import Profile
from library.services import PageContextBuilder, SafeRedirectService


class LandingView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect("library:dashboard")
        return render(request, "library/landing.html", {"active_role": "guest"})


class RoleSelectionMixin:
    """Normalize the public student/teacher role selection."""

    def selected_role(self, request):
        requested = request.POST.get("role") or request.GET.get(
            "role", Profile.Role.STUDENT
        )
        return (
            Profile.Role.TEACHER
            if requested == Profile.Role.TEACHER
            else Profile.Role.STUDENT
        )


class RegisterView(RoleSelectionMixin, View):
    template_name = "library/register.html"

    def get(self, request):
        return self._handle(request)

    def post(self, request):
        return self._handle(request)

    def _handle(self, request):
        if request.user.is_authenticated:
            return redirect("library:dashboard")
        selected_role = self.selected_role(request)
        form = RegistrationForm(
            request.POST or None,
            initial={"role": selected_role},
            privacy_consent_version=settings.PRIVACY_CONSENT_VERSION,
        )
        if request.method == "POST" and form.is_valid():
            user = form.save()
            setup_user_email(request, user, [])
            request.session.pop("guest_mode", None)
            messages.success(request, "Your ATLAS account is ready.")
            return complete_signup(
                request,
                user,
                email_verification=allauth_account_settings.EMAIL_VERIFICATION,
                success_url=reverse("library:dashboard"),
            )
        return render(
            request,
            self.template_name,
            {"form": form, "active_role": "guest", "selected_role": selected_role},
        )


class LoginView(RoleSelectionMixin, View):
    template_name = "library/login.html"

    def get(self, request):
        return self._handle(request)

    def post(self, request):
        return self._handle(request)

    def _handle(self, request):
        if request.user.is_authenticated:
            return redirect("library:dashboard")
        selected_role = self.selected_role(request)
        login_data = request.POST.copy() if request.method == "POST" else None
        if login_data is not None:
            if not login_data.get("email") and login_data.get("username"):
                login_data["email"] = login_data["username"]
            login_data["role"] = selected_role
        form = RoleLoginForm(request, login_data, initial={"role": selected_role})
        if request.method == "POST" and form.is_valid():
            user = form.get_user()
            profile = user.profile
            profile.privacy_consent_accepted_at = timezone.now()
            profile.privacy_consent_version = settings.PRIVACY_CONSENT_VERSION
            profile.save(
                update_fields=(
                    "privacy_consent_accepted_at",
                    "privacy_consent_version",
                    "updated_at",
                )
            )
            request.session.pop("guest_mode", None)
            display_name = PageContextBuilder(request).build("home")["display_name"]
            messages.success(request, f"Welcome back, {display_name}.")
            return perform_login(
                request,
                user,
                email_verification=allauth_account_settings.EMAIL_VERIFICATION,
                redirect_url=SafeRedirectService.resolve(
                    request, "library:dashboard"
                ),
                email=user.email,
            )
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "active_role": "guest",
                "selected_role": selected_role,
                "next": request.POST.get("next") or request.GET.get("next", ""),
            },
        )


class GuestLoginView(View):
    def post(self, request):
        if request.user.is_authenticated:
            auth_logout(request)
        request.session["guest_mode"] = True
        return redirect("library:dashboard")


class LogoutView(View):
    def post(self, request):
        auth_logout(request)
        request.session.pop("guest_mode", None)
        messages.info(request, "You have signed out of ATLAS.")
        return redirect("library:landing")
