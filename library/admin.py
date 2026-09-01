from django.contrib import admin
from django.utils import timezone

from .models import Announcement, ContactMessage, Favorite, LibraryItem, Profile, ResourceViewEvent


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "privacy_consent_version", "updated_at")
    list_filter = ("role", "privacy_consent_version")
    search_fields = ("user__username", "user__email", "user__first_name", "user__last_name")
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(LibraryItem)
class LibraryItemAdmin(admin.ModelAdmin):
    fields = (
        "collection",
        "call_number",
        "title",
        "author",
        "details",
        "file_type",
        "pages",
        "published_on",
        "publication_day_known",
        "cover_image",
        "resource_abstract",
        "created_by",
        "created_at",
        "updated_at",
    )
    list_display = (
        "title",
        "author",
        "collection",
        "file_type",
        "published_on",
        "cover_image",
        "resource_abstract",
        "created_at",
    )
    list_filter = ("collection", "file_type", "published_on", "created_at")
    search_fields = ("title", "author", "call_number", "details")
    autocomplete_fields = ("created_by",)
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"
    list_select_related = ("created_by",)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "item", "created_at")
    search_fields = ("user__email", "user__username", "item__title", "item__call_number")
    autocomplete_fields = ("user", "item")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    fields = ("title", "body", "category", "created_by", "published_at", "created_at", "updated_at")
    list_display = ("title", "category", "publication_status", "published_at", "created_by")
    list_filter = ("category",)
    search_fields = ("title", "body")
    autocomplete_fields = ("created_by",)
    readonly_fields = ("published_at", "created_at", "updated_at")
    date_hierarchy = "published_at"
    actions = ("publish_selected", "unpublish_selected")

    @admin.display(description="Status")
    def publication_status(self, announcement):
        return "Published" if announcement.is_published else "Draft"

    def save_model(self, request, obj, form, change):
        obj.is_featured = False
        if not change:
            obj.is_published = False
            obj.published_at = None
        super().save_model(request, obj, form, change)

    @admin.action(description="Publish selected announcements")
    def publish_selected(self, request, queryset):
        queryset.update(is_featured=False, is_published=True, published_at=timezone.now())

    @admin.action(description="Return selected announcements to draft")
    def unpublish_selected(self, request, queryset):
        queryset.update(is_published=False, published_at=None)


@admin.register(ResourceViewEvent)
class ResourceViewEventAdmin(admin.ModelAdmin):
    list_display = ("item", "display_name", "role", "first_viewed_at", "last_viewed_at")
    list_filter = ("role", "first_viewed_at", "last_viewed_at")
    search_fields = (
        "item__title",
        "item__call_number",
        "user__email",
        "user__first_name",
        "user__last_name",
    )
    readonly_fields = (
        "item",
        "user",
        "session_key",
        "role",
        "first_viewed_at",
        "last_viewed_at",
        "ip_address",
    )
    date_hierarchy = "last_viewed_at"

    def has_add_permission(self, request):
        return False


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("subject", "name", "email", "is_resolved", "created_at")
    list_filter = ("is_resolved", "created_at")
    search_fields = ("subject", "name", "email", "message")
    readonly_fields = ("user", "name", "email", "subject", "message", "created_at")
    date_hierarchy = "created_at"
    actions = ("mark_resolved", "mark_unresolved")

    @admin.action(description="Mark selected messages resolved")
    def mark_resolved(self, request, queryset):
        queryset.update(is_resolved=True)

    @admin.action(description="Mark selected messages unresolved")
    def mark_unresolved(self, request, queryset):
        queryset.update(is_resolved=False)
