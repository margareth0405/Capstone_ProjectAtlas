"""Authentication and session views."""

import logging
import smtplib

from allauth.account import app_settings as allauth_account_settings
from allauth.account.utils import complete_signup, perform_login, setup_user_email
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from library.forms import RegistrationForm, RoleLoginForm
from library.models import ActivityLog, Profile
from library.services import PageContextBuilder, SafeRedirectService
from library.services.activity import ActivityRecorder

logger = logging.getLogger(__name__)


class EmailDeliveryErrorMixin:
    """Turn temporary SMTP failures into recoverable form errors."""

    email_error_message = (
        "ATLAS could not send the verification email right now. "
        "Please try again or contact support."
    )
    email_exceptions = (smtplib.SMTPException, OSError)

    def handle_email_error(self, request, form):
        logger.exception("Account email delivery failed.")
        if request.user.is_authenticated:
            auth_logout(request)
        form.add_error(None, self.email_error_message)
        messages.error(request, self.email_error_message)


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


class RegisterView(EmailDeliveryErrorMixin, RoleSelectionMixin, View):
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
        email_failed = False
        if request.method == "POST" and form.is_valid():
            try:
                # Keep account creation and its allauth email identity together.
                # A failed mandatory verification email must not leave behind an
                # unusable account that prevents the visitor from trying again.
                with transaction.atomic():
                    user = form.save()
                    ActivityRecorder.record(
                        actor=user,
                        action=ActivityLog.Action.CREATE,
                        object_type="user account",
                        object_id=user.pk,
                        description=user.email,
                    )
                    setup_user_email(request, user, [])
                    response = complete_signup(
                        request,
                        user,
                        email_verification=allauth_account_settings.EMAIL_VERIFICATION,
                        success_url=reverse("library:dashboard"),
                    )
            except self.email_exceptions:
                self.handle_email_error(request, form)
                email_failed = True
            else:
                request.session.pop("guest_mode", None)
                messages.success(request, "Your ATLAS account is ready.")
                return response
        if request.method == "POST" and not email_failed:
            messages.error(
                request,
                "Registration was not completed. Review the highlighted fields.",
            )
        return render(
            request,
            self.template_name,
            {"form": form, "active_role": "guest", "selected_role": selected_role},
        )


class LoginView(EmailDeliveryErrorMixin, RoleSelectionMixin, View):
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
        email_failed = False
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
            try:
                response = perform_login(
                    request,
                    user,
                    email_verification=allauth_account_settings.EMAIL_VERIFICATION,
                    redirect_url=SafeRedirectService.resolve(
                        request, "library:dashboard"
                    ),
                    email=user.email,
                )
            except self.email_exceptions:
                self.handle_email_error(request, form)
                email_failed = True
            else:
                messages.success(request, f"Welcome back, {display_name}.")
                return response
        if request.method == "POST" and not email_failed:
            messages.error(
                request,
                "Sign-in was not completed. Review your details and try again.",
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
        messages.success(request, "Guest access is ready. Welcome to ATLAS.")
        return redirect("library:dashboard")


class LogoutView(View):
    def post(self, request):
        auth_logout(request)
        request.session.pop("guest_mode", None)
        messages.info(request, "You have signed out of ATLAS.")
        return redirect("library:landing")
