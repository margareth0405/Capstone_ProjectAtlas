"""Shared test data helpers for the library application."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from library.models import Announcement, LibraryItem, Profile


TEST_PASSWORD = "Atlas-Test-Pass-2026!"


class LibraryTestCase(TestCase):
    """Create users through Django's authentication API in every test."""

    def create_user(
        self,
        *,
        email="student@example.com",
        password=TEST_PASSWORD,
        role=Profile.Role.STUDENT,
        is_staff=False,
        is_superuser=False,
    ):
        user = get_user_model().objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name="Atlas",
            last_name="User",
            is_staff=is_staff,
            is_superuser=is_superuser,
        )
        # Most application code creates this through a post_save signal. Using
        # get_or_create here keeps unrelated view tests focused; the signal
        # itself has a dedicated contract test.
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.role = role
        profile.save(update_fields=["role", "updated_at"])
        return user

    def create_item(self, **overrides):
        values = {
            "collection": LibraryItem.Collection.BOOK,
            "call_number": "QA76.73-T001",
            "title": "Django Testing Handbook",
            "author": "Atlas Library",
            "details": "A digital resource used by the automated tests.",
            "file_type": "PDF",
            "file_size": "1.2 MB",
            "pages": 120,
            "external_url": "https://example.com/resources/django-testing.pdf",
        }
        values.update(overrides)
        return LibraryItem.objects.create(**values)

    def create_announcement(self, **overrides):
        values = {
            "title": "Library update",
            "body": "A new collection is now available.",
            "category": Announcement.Category.RESOURCE,
            "is_featured": False,
            "is_published": True,
            "published_at": timezone.now(),
        }
        values.update(overrides)
        return Announcement.objects.create(**values)
