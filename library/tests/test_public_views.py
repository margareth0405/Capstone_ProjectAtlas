"""Guest pages and member-only catalog actions."""

from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from library.models import ContactMessage, Favorite, Profile, ResourceViewEvent

from library.views.catalog import ResourceReaderView

from .base import LibraryTestCase


class GuestPageTests(LibraryTestCase):
    def test_landing_catalog_announcements_and_contact_are_public(self):
        for route_name in ("landing", "catalog", "announcements", "contact"):
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(f"library:{route_name}"))
                self.assertEqual(response.status_code, 200)

    def test_guest_can_browse_catalog_data(self):
        item = self.create_item()

        response = self.client.get(reverse("library:catalog"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, item.title)

    def test_only_published_announcements_are_visible_to_guests(self):
        published = self.create_announcement(title="Visible announcement")
        hidden = self.create_announcement(
            title="Draft announcement", is_published=False, published_at=None
        )

        response = self.client.get(reverse("library:announcements"))

        self.assertContains(response, published.title)
        self.assertNotContains(response, hidden.title)


class AnnouncementAndCatalogVisibilityTests(LibraryTestCase):
    def test_published_announcement_is_visible_to_guest_student_and_teacher(self):
        published = self.create_announcement(title="Role-visible announcement")
        draft = self.create_announcement(
            title="Staff-only draft",
            is_published=False,
            published_at=None,
        )

        guest_response = self.client.get(reverse("library:announcements"))
        self.assertContains(guest_response, published.title)
        self.assertNotContains(guest_response, draft.title)

        for role in (Profile.Role.STUDENT, Profile.Role.TEACHER):
            with self.subTest(role=role):
                self.client.force_login(
                    self.create_user(email=f"{role}@example.com", role=role)
                )
                response = self.client.get(reverse("library:announcements"))
                self.assertContains(response, published.title)
                self.assertNotContains(response, draft.title)
                self.client.logout()

    def test_library_page_links_latest_published_announcement(self):
        announcement = self.create_announcement(title="New catalog notice")
        response = self.client.get(reverse("library:catalog"))

        self.assertContains(response, "Latest announcements")
        self.assertContains(response, announcement.title)
        self.assertContains(
            response,
            f'{reverse("library:announcements")}#announcement-{announcement.pk}',
        )

    def test_catalog_sorts_title_author_and_publication_date_both_directions(self):
        alpha = self.create_item(
            call_number="SORT-A",
            title="Alpha",
            author="Zulu Author",
            published_on=date(2023, 5, 1),
        )
        beta = self.create_item(
            call_number="SORT-B",
            title="Beta",
            author="Alpha Author",
            published_on=date(2025, 6, 1),
        )

        cases = (
            ("title", [alpha, beta]),
            ("-title", [beta, alpha]),
            ("author", [beta, alpha]),
            ("-author", [alpha, beta]),
            ("published_newest", [beta, alpha]),
            ("published_oldest", [alpha, beta]),
        )
        for sort_value, expected in cases:
            with self.subTest(sort=sort_value):
                response = self.client.get(
                    reverse("library:catalog"), {"sort": sort_value}
                )
                self.assertEqual(list(response.context["items"]), expected)

    def test_catalog_and_saved_page_use_bookmark_and_abstract_labels(self):
        item = self.create_item()
        user = self.create_user(email="bookmark-reader@example.com")
        self.client.force_login(user)

        catalog_response = self.client.get(reverse("library:catalog"))
        bookmarks_response = self.client.get(reverse("library:favorites"))

        self.assertContains(catalog_response, "View abstract")
        self.assertContains(catalog_response, "Bookmark")
        self.assertContains(catalog_response, item.publication_date_display)
        self.assertContains(bookmarks_response, "Bookmarks")
        self.assertNotContains(bookmarks_response, ">Favorites<")

@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    SUPPORT_EMAIL="atlastshs@gmail.com",
)
class ContactTests(LibraryTestCase):
    def contact_payload(self):
        return {
            "name": "A Library Visitor",
            "email": "visitor@example.com",
            "subject": "Research support",
            "message": "Please help me find a research paper.",
        }

    def test_contact_get_does_not_create_a_message(self):
        response = self.client.get(reverse("library:contact"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactMessage.objects.count(), 0)

    def test_guest_can_submit_contact_message_by_post(self):
        response = self.client.post(
            reverse("library:contact"), self.contact_payload()
        )

        self.assertEqual(response.status_code, 302)
        message = ContactMessage.objects.get()
        self.assertEqual(message.email, "visitor@example.com")
        self.assertIsNone(message.user)
        self.assertEqual(len(mail.outbox), 1)
        delivered = mail.outbox[0]
        self.assertEqual(delivered.to, ["atlastshs@gmail.com"])
        self.assertEqual(delivered.reply_to, ["visitor@example.com"])
        self.assertIn("Name: A Library Visitor", delivered.body)
        self.assertIn("Email: visitor@example.com", delivered.body)
        self.assertIn("Please help me find a research paper.", delivered.body)

    def test_authenticated_contact_message_is_linked_to_user(self):
        user = self.create_user(email="contact-user@example.com")
        self.client.force_login(user)

        response = self.client.post(
            reverse("library:contact"), self.contact_payload()
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(ContactMessage.objects.get().user, user)


class FavoriteTests(LibraryTestCase):
    def setUp(self):
        self.item = self.create_item()

    def favorite_url(self):
        return reverse("library:favorite_toggle", args=[self.item.pk])

    def test_anonymous_user_cannot_favorite_an_item(self):
        response = self.client.post(self.favorite_url())

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("library:login"), response.url)
        self.assertEqual(Favorite.objects.count(), 0)

    def test_favorite_toggle_is_post_only(self):
        user = self.create_user()
        self.client.force_login(user)

        response = self.client.get(self.favorite_url())

        self.assertEqual(response.status_code, 405)
        self.assertEqual(Favorite.objects.count(), 0)

    def test_member_can_add_and_remove_a_favorite(self):
        user = self.create_user()
        self.client.force_login(user)

        add_response = self.client.post(self.favorite_url())
        self.assertEqual(add_response.status_code, 302)
        self.assertTrue(Favorite.objects.filter(user=user, item=self.item).exists())

        remove_response = self.client.post(self.favorite_url())
        self.assertEqual(remove_response.status_code, 302)
        self.assertFalse(
            Favorite.objects.filter(user=user, item=self.item).exists()
        )


class ResourceReaderTests(LibraryTestCase):
    class StubExtractor:
        def extract_for_reading(self, resource):
            return "Protected resource text shown inside ATLAS."

    def setUp(self):
        self.item = self.create_item(
            external_url="",
            resource=SimpleUploadedFile(
                "protected.pdf",
                b"%PDF-1.4 protected fixture",
                content_type="application/pdf",
            ),
        )
        self.url = reverse("library:resource_reader", args=[self.item.pk])

    def test_catalog_has_read_action_and_no_download_action_for_every_role(self):
        for role in ("guest", Profile.Role.STUDENT, Profile.Role.TEACHER):
            with self.subTest(role=role):
                if role != "guest":
                    self.client.force_login(
                        self.create_user(email=f"reader-{role}@example.com", role=role)
                    )
                response = self.client.get(reverse("library:catalog"))
                self.assertContains(response, "Read resource")
                self.assertNotContains(response, ">Download<")
                self.client.logout()

    def test_reader_displays_extracted_text_and_deduplicates_refreshes(self):
        teacher = self.create_user(
            email="viewer-teacher@example.com",
            role=Profile.Role.TEACHER,
        )
        self.client.force_login(teacher)

        with patch.object(ResourceReaderView, "extractor_class", self.StubExtractor):
            first_response = self.client.get(self.url)
            refresh_response = self.client.get(self.url)

        self.assertContains(first_response, "Protected resource text shown inside ATLAS.")
        self.assertEqual(refresh_response.status_code, 200)
        event = ResourceViewEvent.objects.get()
        self.assertEqual(event.user, teacher)
        self.assertEqual(event.item, self.item)
        self.assertEqual(event.role, Profile.Role.TEACHER)

    def test_guest_can_read_and_is_recorded_as_guest(self):
        with patch.object(ResourceReaderView, "extractor_class", self.StubExtractor):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        event = ResourceViewEvent.objects.get()
        self.assertIsNone(event.user)
        self.assertEqual(event.role, "guest")

    def test_original_media_file_is_not_publicly_routed(self):
        response = self.client.get(f"/media/{self.item.resource.name}")

        self.assertEqual(response.status_code, 404)
    def test_old_download_path_is_not_available(self):
        response = self.client.get(f"/library/{self.item.pk}/download/")

        self.assertEqual(response.status_code, 404)