"""Administrator account and download-record management views."""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from library.forms import AdminCreatedUserForm
from library.models import ActivityLog, DownloadEvent
from library.services import PageContextBuilder
from library.services.activity import ActivityRecorder

from .mixins import StaffRequiredMixin


class StaffUserCreateView(StaffRequiredMixin, View):
    """Create a student or teacher account from the staff portal."""

    template_name = "library/admin/user_form.html"
    form_class = AdminCreatedUserForm
    activity_recorder_class = ActivityRecorder

    def get(self, request):
        return self._render(self.form_class())

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
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

    def post(self, request, pk):
        account = get_object_or_404(self.user_model, pk=pk)
        if account == request.user:
            messages.error(
                request,
                "You cannot delete the account you are currently using.",
            )
        elif account.is_superuser:
            messages.error(
                request,
                "Superuser accounts must be managed in Django admin.",
            )
        else:
            email = account.email or account.username
            account.delete()
            self.activity_recorder_class.record(
                actor=request.user,
                action=ActivityLog.Action.DELETE,
                object_type="user account",
                object_id=pk,
                description=email,
            )
            messages.info(request, f"Account deleted for {email}.")
        return redirect("library:staff_portal")


class StaffDownloadDeleteView(StaffRequiredMixin, View):
    """Delete one download record without deleting its resource or user."""

    activity_recorder_class = ActivityRecorder

    def post(self, request, pk):
        event = get_object_or_404(
            DownloadEvent.objects.select_related("user", "item"),
            pk=pk,
        )
        user_label = event.user.email if event.user else "Unknown user"
        description = f"{event.item.title} — {user_label}"
        event.delete()
        self.activity_recorder_class.record(
            actor=request.user,
            action=ActivityLog.Action.DELETE,
            object_type="download record",
            object_id=pk,
            description=description,
        )
        messages.info(request, "Download record deleted.")
        return redirect("library:staff_portal")
