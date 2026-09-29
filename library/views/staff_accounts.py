"""Administrator account management views."""

import logging

from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from library.forms import AdminCreatedUserForm, StaffAccountUpdateForm
from library.models import ActivityLog
from library.services import PageContextBuilder
from library.services.activity import ActivityRecorder

from .mixins import StaffRequiredMixin

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
                return redirect("library:staff_portal")
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


class StaffUserDeleteView(StaffRequiredMixin, View):
    """Delete a reader account while protecting active staff credentials."""

    activity_recorder_class = ActivityRecorder
    user_model = get_user_model()

    @staticmethod
    def users_url():
        """Return staff to the account list instead of the portal's first tab."""
        return f'{reverse("library:staff_portal")}#users'

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
        elif account.is_staff or account.is_superuser:
            messages.error(
                request,
                "Administrator accounts cannot be deleted from the staff portal.",
            )
        else:
            email = account.email or account.username
            try:
                with transaction.atomic():
                    account.delete()
                    self.activity_recorder_class.record(
                        actor=request.user,
                        action=ActivityLog.Action.DELETE,
                        object_type="user account",
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
    form_class = StaffAccountUpdateForm
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
        return self._render(
            account,
            self.form_class(actor=request.user, account=account),
        )

    def post(self, request, pk=None):
        account = self.account_for(request, pk)
        form = self.form_class(
            request.POST,
            actor=request.user,
            account=account,
        )
        if not form.is_valid():
            messages.error(request, "The administrator account was not updated.")
            return self._render(account, form)

        try:
            with transaction.atomic():
                updated_account = form.save()
                self.activity_recorder_class.record(
                    actor=request.user,
                    action=ActivityLog.Action.UPDATE,
                    object_type="administrator account",
                    object_id=updated_account.pk,
                    description=updated_account.get_username(),
                )
        except DatabaseError:
            logger.exception("Administrator account update failed for %s", account.pk)
            form.add_error(
                None,
                "ATLAS could not update the administrator account. No changes "
                "were saved. Try again after the database is available.",
            )
            messages.error(request, "The administrator account was not updated.")
            return self._render(account, form)

        if updated_account == request.user and form.password_changed:
            update_session_auth_hash(request, updated_account)
        messages.success(request, "Administrator account settings updated.")
        if updated_account == request.user:
            return redirect("library:staff_account_edit")
        return redirect(f'{reverse("library:staff_portal")}#users')

    def _render(self, account, form):
        editing_self = account == self.request.user
        context = PageContextBuilder(self.request).build("users")
        context.update(
            {
                "account": account,
                "editing_self": editing_self,
                "form": form,
                "cancel_url": (
                    reverse("library:staff_portal") + "#users"
                    if not editing_self
                    else reverse("library:staff_portal")
                ),
            }
        )
        return render(self.request, self.template_name, context)
