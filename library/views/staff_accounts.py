"""Administrator account management views."""

import logging

from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from library.forms import (
    AdminCreatedUserForm,
    StaffPasswordChangeForm,
    StaffUsernameUpdateForm,
    SuperuserCreatedAdminForm,
)
from library.models import ActivityLog
from library.services import PageContextBuilder
from library.services.activity import ActivityRecorder

from .mixins import StaffRequiredMixin, SuperuserRequiredMixin

logger = logging.getLogger(__name__)


class StaffUserCreateView(StaffRequiredMixin, View):
    """Create a student or teacher account from the staff portal."""

    template_name = "library/admin/user_form.html"
    form_class = AdminCreatedUserForm
    activity_recorder_class = ActivityRecorder

    def get(self, request):
        return self._render(self.form_class())

    def post(self, request):
        form = self.form_class(request.POST)
        try:
            if form.is_valid():
                with transaction.atomic():
                    user = form.save()
                    self.activity_recorder_class.record(
                        actor=request.user,
                        action=ActivityLog.Action.CREATE,
                        object_type="user account",
                        object_id=user.pk,
                        description=user.email,
                    )
                messages.success(request, f"Account created for {user.email}.")
                return redirect("library:staff_users")
        except DatabaseError:
            logger.exception("Staff account creation failed and was rolled back")
            form.add_error(
                None,
                "ATLAS could not create the account because the database is not "
                "ready. No account was added. Ask an administrator to apply the "
                "latest migrations, then try again.",
            )
            messages.error(request, "The account could not be created.")
            return self._render(form)
        messages.error(
            request,
            "The account was not created. Review the highlighted fields.",
        )
        return self._render(form)

    def _render(self, form):
        context = PageContextBuilder(self.request).build("users")
        context.update(
            {
                "form": form,
                "form_title": "Create account",
                "submit_label": "Create account",
            }
        )
        return render(self.request, self.template_name, context)


class SuperuserAdminCreateView(SuperuserRequiredMixin, View):
    """Allow only a superuser to create a regular administrator account."""

    template_name = "library/admin/administrator_form.html"
    form_class = SuperuserCreatedAdminForm
    activity_recorder_class = ActivityRecorder

    def get(self, request):
        return self._render(self.form_class(actor=request.user))

    def post(self, request):
        form = self.form_class(request.POST, actor=request.user)
        try:
            if form.is_valid():
                with transaction.atomic():
                    administrator = form.save()
                    self.activity_recorder_class.record(
                        actor=request.user,
                        action=ActivityLog.Action.CREATE,
                        object_type="administrator account",
                        object_id=administrator.pk,
                        description=administrator.email,
                    )
                messages.success(
                    request,
                    f"Administrator account created for {administrator.email}.",
                )
                return redirect("library:staff_users")
        except DatabaseError:
            logger.exception("Administrator account creation failed and was rolled back")
            form.add_error(
                None,
                "ATLAS could not create the administrator account. No account "
                "was added. Try again after the database is available.",
            )
            messages.error(request, "The administrator account could not be created.")
            return self._render(form)
        messages.error(
            request,
            "The administrator account was not created. Review the highlighted fields.",
        )
        return self._render(form)

    def _render(self, form):
        context = PageContextBuilder(self.request).build("users")
        context.update({"form": form})
        return render(self.request, self.template_name, context)


class StaffUserDeleteView(StaffRequiredMixin, View):
    """Delete readers, or let a superuser delete a regular administrator."""

    activity_recorder_class = ActivityRecorder
    user_model = get_user_model()

    @staticmethod
    def users_url():
        """Return staff to the account list instead of the portal's first tab."""
        return reverse("library:staff_users")

    def post(self, request, pk):
        try:
            account = get_object_or_404(self.user_model, pk=pk)
        except DatabaseError:
            logger.exception("Could not load account %s for deletion", pk)
            messages.error(
                request,
                "ATLAS could not access that account. Ask an administrator to "
                "verify the database migrations, then try again.",
            )
            return redirect(self.users_url())
        if account == request.user:
            messages.error(
                request,
                "You cannot delete the account you are currently using.",
            )
        elif account.is_superuser:
            messages.error(
                request,
                "Superuser accounts cannot be deleted from the staff portal.",
            )
        elif account.is_staff and not request.user.is_superuser:
            messages.error(
                request,
                "Only a Superuser can delete an Administrator account.",
            )
        else:
            email = account.email or account.username
            object_type = (
                "administrator account" if account.is_staff else "user account"
            )
            try:
                with transaction.atomic():
                    account.delete()
                    self.activity_recorder_class.record(
                        actor=request.user,
                        action=ActivityLog.Action.DELETE,
                        object_type=object_type,
                        object_id=pk,
                        description=email,
                    )
            except DatabaseError:
                logger.exception(
                    "Staff account deletion failed and was rolled back for %s",
                    pk,
                )
                messages.error(
                    request,
                    "ATLAS could not delete the account. No changes were saved. "
                    "Ask an administrator to apply the latest database migrations, "
                    "then try again.",
                )
            else:
                messages.info(request, f"Account deleted for {email}.")
        return redirect(self.users_url())


class StaffAccountEditView(StaffRequiredMixin, View):
    """Edit the current administrator or, for superusers, another admin."""

    template_name = "library/admin/account_form.html"
    username_form_class = StaffUsernameUpdateForm
    password_form_class = StaffPasswordChangeForm
    user_model = get_user_model()
    activity_recorder_class = ActivityRecorder

    def account_for(self, request, pk=None):
        account = request.user if pk is None else get_object_or_404(self.user_model, pk=pk)
        if not (account.is_staff or account.is_superuser):
            raise PermissionDenied
        if account != request.user and not request.user.is_superuser:
            raise PermissionDenied
        return account

    def get(self, request, pk=None):
        account = self.account_for(request, pk)
        return self._render(account)

    def post(self, request, pk=None):
        account = self.account_for(request, pk)
        action = request.POST.get("account_action")
        username_form = self._username_form(
            account,
            request.POST if action == "username" else None,
        )
        password_form = self._password_form(
            account,
            request.POST if action == "password" else None,
        )
        account_type = "Superuser" if account.is_superuser else "Administrator"

        if action == "username":
            form = username_form
            success_message = f"{account_type} username updated. Password unchanged."
        elif action == "password":
            form = password_form
            success_message = f"{account_type} password changed. Username unchanged."
        else:
            username_form.add_error(
                None, "Choose the account setting you want to update."
            )
            messages.error(request, "The administrator account was not updated.")
            return self._render(account, username_form, password_form)

        if not form.is_valid():
            messages.error(request, "The administrator account was not updated.")
            return self._render(account, username_form, password_form)

        activity_description = (
            f"Username changed to {form.cleaned_data['username']}"
            if action == "username"
            else "Password changed"
        )

        try:
            with transaction.atomic():
                updated_account = form.save()
                self.activity_recorder_class.record(
                    actor=request.user,
                    action=ActivityLog.Action.UPDATE,
                    object_type="administrator account",
                    object_id=updated_account.pk,
                    description=activity_description,
                )
        except DatabaseError:
            logger.exception("Administrator account update failed for %s", account.pk)
            form.add_error(
                None,
                "ATLAS could not update the administrator account. No changes "
                "were saved. Try again after the database is available.",
            )
            messages.error(request, "The administrator account was not updated.")
            return self._render(account, username_form, password_form)

        if action == "password" and updated_account == request.user:
            update_session_auth_hash(request, updated_account)
        messages.success(request, success_message)
        if updated_account == request.user:
            return redirect("library:staff_account_edit")
        return redirect("library:staff_users")

    def _username_form(self, account, data=None):
        return self.username_form_class(
            data,
            actor=self.request.user,
            account=account,
            prefix="username",
        )

    def _password_form(self, account, data=None):
        return self.password_form_class(
            data,
            actor=self.request.user,
            account=account,
            prefix="password",
        )

    def _render(self, account, username_form=None, password_form=None):
        editing_self = account == self.request.user
        context = PageContextBuilder(self.request).build("users")
        context.update(
            {
                "account": account,
                "editing_self": editing_self,
                "username_form": username_form or self._username_form(account),
                "password_form": password_form or self._password_form(account),
                "cancel_url": (
                    reverse("library:staff_users")
                    if not editing_self
                    else reverse("library:staff_portal")
                ),
            }
        )
        return render(self.request, self.template_name, context)
