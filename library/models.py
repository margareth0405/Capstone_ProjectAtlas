from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.formats import date_format


class Profile(models.Model):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        TEACHER = "teacher", "Teacher"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    privacy_consent_accepted_at = models.DateTimeField(null=True, blank=True)
    privacy_consent_version = models.CharField(max_length=32, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("user__email",)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.get_username()} ({self.get_role_display()})"


class LibraryItem(models.Model):
    class Collection(models.TextChoices):
        BOOK = "book", "Book"
        JOURNAL = "journal", "Journal"
        RESEARCH = "research", "Research"
        ACTIVITY_SHEETS = "activity_sheets", "Activity Sheets"
        CURRICULUM_GUIDE = "curriculum_guide", "Curriculum Guide"

    class FileType(models.TextChoices):
        PDF = "PDF", "PDF"
        WORD = "WORD", "Word document"

    collection = models.CharField(max_length=32, choices=Collection.choices, db_index=True)
    call_number = models.CharField(max_length=80, unique=True)
    title = models.CharField(max_length=255, db_index=True)
    author = models.CharField(max_length=255, db_index=True)
    details = models.TextField(blank=True)
    file_type = models.CharField(
        max_length=20,
        choices=FileType.choices,
        default=FileType.PDF,
    )
    file_size = models.CharField(max_length=32, blank=True)
    pages = models.PositiveIntegerField(default=0)
    resource = models.FileField(upload_to="library/resources/%Y/%m/", blank=True)
    published_on = models.DateField(null=True, blank=True, db_index=True)
    publication_day_known = models.BooleanField(default=False)
    external_url = models.URLField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_library_items",
    )
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("title", "author")
        indexes = [
            models.Index(fields=("collection", "title"), name="library_col_title_idx"),
        ]

    def clean(self):
        super().clean()
        self.call_number = self.call_number.strip()
        self.file_type = self.file_type.strip().upper()
        if self.resource and self.external_url:
            raise ValidationError(
                "Provide either an uploaded resource or an external URL, not both."
            )


    @property
    def publication_date_display(self):
        if not self.published_on:
            return "Not specified"
        output_format = "F j, Y" if self.publication_day_known else "F Y"
        return date_format(self.published_on, output_format)

    def __str__(self):
        return f"{self.title} ({self.call_number})"


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorite_links",
    )
    item = models.ForeignKey(
        LibraryItem,
        on_delete=models.CASCADE,
        related_name="favorite_links",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Bookmark"
        verbose_name_plural = "Bookmarks"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("user", "item"), name="unique_user_library_favorite"
            )
        ]

    def __str__(self):
        return f"{self.user} → {self.item}"


class DownloadEvent(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="download_events",
    )
    item = models.ForeignKey(
        LibraryItem,
        on_delete=models.CASCADE,
        related_name="download_events",
    )
    downloaded_at = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ("-downloaded_at",)

    def __str__(self):
        return f"{self.item} downloaded at {self.downloaded_at:%Y-%m-%d %H:%M}"


class Announcement(models.Model):
    class Category(models.TextChoices):
        GENERAL = "general", "General"
        EVENT = "event", "Event"
        MAINTENANCE = "maintenance", "Maintenance"
        RESOURCE = "resource", "Resource"
        URGENT = "urgent", "Urgent"
        OTHER = "other", "Other"

    title = models.CharField(max_length=255)
    body = models.TextField()
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.GENERAL, db_index=True
    )
    is_featured = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="announcements_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-published_at", "-created_at")
        constraints = [
            models.CheckConstraint(
                condition=Q(is_published=False) | Q(published_at__isnull=False),
                name="published_announcement_has_date",
            )
        ]

    def clean(self):
        super().clean()
        if self.is_published and not self.published_at:
            self.published_at = timezone.now()

    def save(self, *args, **kwargs):
        if self.is_published and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class ContactMessage(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="contact_messages",
    )
    name = models.CharField(max_length=150)
    email = models.EmailField()
    subject = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    is_resolved = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.subject} — {self.email}"

class ActivityLog(models.Model):
    """Durable staff-facing history for important ATLAS changes and downloads."""

    class Action(models.TextChoices):
        CREATE = "create", "Created"
        UPDATE = "update", "Updated"
        DELETE = "delete", "Deleted"
        DOWNLOAD = "download", "Downloaded"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="atlas_activity",
    )
    action = models.CharField(max_length=20, choices=Action.choices, db_index=True)
    object_type = models.CharField(max_length=40, db_index=True)
    object_id = models.CharField(max_length=64, blank=True)
    description = models.CharField(max_length=500)
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-occurred_at", "-id")

    def __str__(self):
        return f"{self.get_action_display()} {self.object_type}: {self.description}"


class WebsiteVisit(models.Model):
    """Approximate active time for an authenticated user or guest browser session."""

    class Role(models.TextChoices):
        GUEST = "guest", "Guest"
        STUDENT = "student", "Student"
        TEACHER = "teacher", "Teacher"
        ADMINISTRATOR = "administrator", "Administrator"

    session_key = models.CharField(max_length=40, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="website_visits",
    )
    role = models.CharField(max_length=20, choices=Role.choices, db_index=True)
    started_at = models.DateTimeField(auto_now_add=True, db_index=True)
    last_seen_at = models.DateTimeField(auto_now_add=True, db_index=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    page_views = models.PositiveIntegerField(default=0)
    last_path = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ("-last_seen_at",)
        indexes = [
            models.Index(
                fields=("session_key", "started_at"), name="visit_session_start_idx"
            )
        ]

    @property
    def display_name(self):
        if self.user:
            return self.user.get_full_name() or self.user.email or self.user.username
        return "Guest visitor"

    def __str__(self):
        return f"{self.display_name} ({self.get_role_display()})"


class ResourceViewEvent(models.Model):
    """A deduplicated record of a visitor reading one library resource."""

    item = models.ForeignKey(
        LibraryItem,
        on_delete=models.CASCADE,
        related_name="view_events",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="resource_view_events",
    )
    session_key = models.CharField(max_length=40, db_index=True)
    role = models.CharField(
        max_length=20,
        choices=WebsiteVisit.Role.choices,
        db_index=True,
    )
    first_viewed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    last_viewed_at = models.DateTimeField(auto_now=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ("-last_viewed_at", "-id")
        indexes = [
            models.Index(
                fields=("item", "last_viewed_at"),
                name="resource_view_item_idx",
            )
        ]

    @property
    def display_name(self):
        if self.user:
            return self.user.get_full_name() or self.user.email or self.user.username
        return "Guest visitor"

    def __str__(self):
        return f"{self.display_name} viewed {self.item.title}"

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_user_profile(sender, instance, created, **kwargs):
    """Give every non-staff account a stable role/consent record."""
    if created and not instance.is_staff:
        Profile.objects.get_or_create(user=instance)
