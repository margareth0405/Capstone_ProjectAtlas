from django.contrib import admin
from django.utils import timezone

from .models import Announcement, ContactMessage, DownloadEvent, Favorite, LibraryItem, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "privacy_consent_version", "updated_at")
    list_filter = ("role", "privacy_consent_version")
    search_fields = ("user__username", "user__email", "user__first_name", "user__last_name")
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(LibraryItem)
class LibraryItemAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "collection", "call_number", "file_type", "downloadable", "created_at")
    list_filter = ("collection", "file_type", "created_at")
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


@admin.register(DownloadEvent)
class DownloadEventAdmin(admin.ModelAdmin):
    list_display = ("item", "user", "ip_address", "downloaded_at")
    list_filter = ("downloaded_at",)
    search_fields = ("item__title", "item__call_number", "user__email", "ip_address")
    autocomplete_fields = ("user", "item")
    readonly_fields = ("user", "item", "downloaded_at", "ip_address", "user_agent")
    date_hierarchy = "downloaded_at"

    def has_add_permission(self, request):
        return False


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "is_featured", "is_published", "published_at", "created_by")
    list_filter = ("category", "is_featured", "is_published")
    search_fields = ("title", "body")
    autocomplete_fields = ("created_by",)
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "published_at"
    actions = ("publish_selected", "unpublish_selected")

    @admin.action(description="Publish selected announcements")
    def publish_selected(self, request, queryset):
        queryset.update(is_published=True, published_at=timezone.now())

    @admin.action(description="Unpublish selected announcements")
    def unpublish_selected(self, request, queryset):
        queryset.update(is_published=False)


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
