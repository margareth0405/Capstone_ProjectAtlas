"""Administrator CRUD views for resources and announcements."""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from library.forms import AnnouncementForm, LibraryItemForm
from library.models import ActivityLog, Announcement, LibraryItem
from library.services import PageContextBuilder
from library.services.activity import ActivityRecorder

from .mixins import StaffRequiredMixin


class StaffFormView(StaffRequiredMixin, View):
    """Shared create/edit workflow for staff-managed model forms."""

    form_class = None
    template_name = None
    active_page = "home"
    form_title = ""
    submit_label = "Save"
    success_message = "Saved."
    activity_object_type = "record"
    activity_recorder_class = ActivityRecorder

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

    def get_success_url(self, instance):
        return reverse("library:staff_portal")

    def get(self, request, *args, **kwargs):
        return self.render_form(self.get_form())

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            is_create = form.instance.pk is None
            instance = self.prepare_instance(form.save(commit=False))
            instance.save()
            form.save_m2m()
            self.activity_recorder_class.record(
                actor=request.user,
                action=(
                    ActivityLog.Action.CREATE
                    if is_create
                    else ActivityLog.Action.UPDATE
                ),
                object_type=self.activity_object_type,
                object_id=instance.pk,
                description=str(instance),
            )
            messages.success(request, self.success_message)
            return redirect(self.get_success_url(instance))
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
    """Create one library resource."""

    form_class = LibraryItemForm
    template_name = "library/admin/item_form.html"
    active_page = "catalog"
    form_title = "Add library item"
    submit_label = "Add item"
    activity_object_type = "library resource"

    def prepare_instance(self, instance):
        instance.created_by = self.request.user
        self.success_message = f"{instance.title} was added to the library."
        return instance


class StaffItemEditView(StaffItemCreateView):
    """Edit one existing library resource."""

    form_title = "Edit library item"
    submit_label = "Save changes"

    def get_instance(self):
        return get_object_or_404(LibraryItem, pk=self.kwargs["pk"])

    def prepare_instance(self, instance):
        self.success_message = f"{instance.title} was updated."
        return instance


class StaffItemDeleteView(StaffRequiredMixin, View):
    """Delete one library resource and retain an audit entry."""

    activity_recorder_class = ActivityRecorder

    def post(self, request, pk):
        item = get_object_or_404(LibraryItem, pk=pk)
        title = item.title
        item.delete()
        self.activity_recorder_class.record(
            actor=request.user,
            action=ActivityLog.Action.DELETE,
            object_type="library resource",
            object_id=pk,
            description=title,
        )
        messages.info(request, f"{title} was removed from the library.")
        return redirect("library:staff_portal")


class StaffAnnouncementCreateView(StaffFormView):
    """Create and optionally publish one announcement."""

    form_class = AnnouncementForm
    template_name = "library/admin/announcement_form.html"
    active_page = "announcements"
    form_title = "Create announcement"
    submit_label = "Save announcement"
    activity_object_type = "announcement"

    def prepare_instance(self, instance):
        instance.created_by = self.request.user
        self.success_message = (
            "Announcement published."
            if instance.is_published
            else "Announcement saved as a draft."
        )
        return instance

    def get_success_url(self, instance):
        return f'{reverse("library:announcements")}#announcement-{instance.pk}'


class StaffAnnouncementEditView(StaffAnnouncementCreateView):
    """Edit one existing announcement."""

    form_title = "Edit announcement"
    submit_label = "Save changes"

    def get_instance(self):
        return get_object_or_404(Announcement, pk=self.kwargs["pk"])

    def prepare_instance(self, instance):
        self.success_message = (
            "Announcement updated and published."
            if instance.is_published
            else "Announcement updated as a draft."
        )
        return instance


class StaffAnnouncementDeleteView(StaffRequiredMixin, View):
    """Delete one announcement and retain an audit entry."""

    activity_recorder_class = ActivityRecorder

    def post(self, request, pk):
        announcement = get_object_or_404(Announcement, pk=pk)
        title = announcement.title
        announcement.delete()
        self.activity_recorder_class.record(
            actor=request.user,
            action=ActivityLog.Action.DELETE,
            object_type="announcement",
            object_id=pk,
            description=title,
        )
        messages.info(request, f"{title} was deleted.")
        return redirect("library:announcements")
