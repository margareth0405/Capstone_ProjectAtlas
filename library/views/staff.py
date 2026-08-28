"""Staff dashboard and CRUD views."""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import TemplateView

from library.forms import AdminCreatedUserForm, AnnouncementForm, LibraryItemForm
from library.models import Announcement, ContactMessage, DownloadEvent, LibraryItem, Profile
from library.services import PageContextBuilder

from .mixins import PageContextMixin, StaffRequiredMixin


class StaffPortalView(StaffRequiredMixin, PageContextMixin, TemplateView):
    template_name = "library/staff_portal.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        users = get_user_model().objects.select_related("profile").order_by("-date_joined")
        context["stats"].update(
            {
                "total_users": users.count(),
                "student_users": users.filter(profile__role=Profile.Role.STUDENT).count(),
                "teacher_users": users.filter(profile__role=Profile.Role.TEACHER).count(),
                "successful_logins": users.filter(last_login__isnull=False).count(),
            }
        )
        context.update(
            {
                "items": LibraryItem.objects.order_by("-created_at"),
                "recent_items": LibraryItem.objects.order_by("-created_at")[:8],
                "announcements": Announcement.objects.all(),
                "recent_announcements": Announcement.objects.all()[:6],
                "users": users,
                "user_count": users.count(),
                "download_count": DownloadEvent.objects.count(),
                "message_count": ContactMessage.objects.filter(is_resolved=False).count(),
                "item_form": LibraryItemForm(),
                "announcement_form": AnnouncementForm(),
                "user_form": AdminCreatedUserForm(),
            }
        )
        return context


class StaffFormView(StaffRequiredMixin, View):
    """Shared create/edit workflow for staff-managed model forms."""

    form_class = None
    template_name = None
    active_page = "home"
    form_title = ""
    submit_label = "Save"
    success_message = "Saved."

    def get_instance(self):
        return None

    def get_form(self):
        kwargs = {"instance": self.get_instance()}
        if self.request.method == "POST":
            kwargs["data"] = self.request.POST
            if self.form_class is LibraryItemForm:
                kwargs["files"] = self.request.FILES
        return self.form_class(**kwargs)

    def prepare_instance(self, instance):
        return instance

    def get(self, request, *args, **kwargs):
        return self.render_form(self.get_form())

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            instance = self.prepare_instance(form.save(commit=False))
            instance.save()
            form.save_m2m()
            messages.success(request, self.success_message)
            return redirect("library:staff_portal")
        return self.render_form(form)

    def render_form(self, form):
        context = PageContextBuilder(self.request).build(self.active_page)
        context.update(
            {
                "form": form,
                "form_title": self.form_title,
                "submit_label": self.submit_label,
            }
        )
        return render(self.request, self.template_name, context)


class StaffItemCreateView(StaffFormView):
    form_class = LibraryItemForm
    template_name = "library/admin/item_form.html"
    active_page = "catalog"
    form_title = "Add library item"
    submit_label = "Add item"

    def prepare_instance(self, instance):
        instance.created_by = self.request.user
        self.success_message = f"{instance.title} was added to the library."
        return instance


class StaffItemEditView(StaffItemCreateView):
    form_title = "Edit library item"
    submit_label = "Save changes"

    def get_instance(self):
        return get_object_or_404(LibraryItem, pk=self.kwargs["pk"])

    def prepare_instance(self, instance):
        self.success_message = f"{instance.title} was updated."
        return instance


class StaffItemDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        item = get_object_or_404(LibraryItem, pk=pk)
        title = item.title
        item.delete()
        messages.info(request, f"{title} was removed from the library.")
        return redirect("library:staff_portal")


class StaffAnnouncementCreateView(StaffFormView):
    form_class = AnnouncementForm
    template_name = "library/admin/announcement_form.html"
    active_page = "announcements"
    form_title = "Create announcement"
    submit_label = "Save announcement"
    success_message = "Announcement published."

    def prepare_instance(self, instance):
        instance.created_by = self.request.user
        return instance


class StaffAnnouncementEditView(StaffAnnouncementCreateView):
    form_title = "Edit announcement"
    submit_label = "Save changes"
    success_message = "Announcement updated."

    def get_instance(self):
        return get_object_or_404(Announcement, pk=self.kwargs["pk"])

    def prepare_instance(self, instance):
        return instance


class StaffAnnouncementDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        get_object_or_404(Announcement, pk=pk).delete()
        messages.info(request, "Announcement deleted.")
        return redirect("library:staff_portal")


class StaffUserCreateView(StaffRequiredMixin, View):
    template_name = "library/admin/user_form.html"

    def get(self, request):
        return self._render(AdminCreatedUserForm())

    def post(self, request):
        form = AdminCreatedUserForm(request.POST)
        if form.is_valid():
            user = form.save()
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
