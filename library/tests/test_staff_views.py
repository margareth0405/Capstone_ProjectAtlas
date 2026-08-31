"""Authorization and CRUD behavior for the ATLAS staff portal."""

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from library.models import Announcement, LibraryItem, Profile

from .base import LibraryTestCase, TEST_PASSWORD


class StaffAuthorizationTests(LibraryTestCase):
    def setUp(self):
        self.item = self.create_item()
        self.announcement = self.create_announcement()
        self.nonstaff = self.create_user(email="nonstaff@example.com")

    def protected_requests(self):
        return (
            ("get", reverse("library:staff_portal")),
            ("get", reverse("library:staff_item_create")),
            ("get", reverse("library:staff_item_edit", args=[self.item.pk])),
            ("post", reverse("library:staff_item_delete", args=[self.item.pk])),
            ("get", reverse("library:staff_announcement_create")),
            (
                "get",
                reverse(
                    "library:staff_announcement_edit", args=[self.announcement.pk]
                ),
            ),
            (
                "post",
                reverse(
                    "library:staff_announcement_delete",
                    args=[self.announcement.pk],
                ),
            ),
            ("get", reverse("library:staff_user_create")),
        )

    def test_anonymous_users_are_redirected_from_every_staff_view(self):
        for method, url in self.protected_requests():
            with self.subTest(method=method, url=url):
                response = getattr(self.client, method)(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse("admin:login"), response.url)

    def test_authenticated_nonstaff_users_receive_forbidden(self):
        self.client.force_login(self.nonstaff)

        for method, url in self.protected_requests():
            with self.subTest(method=method, url=url):
                response = getattr(self.client, method)(url)
                self.assertEqual(response.status_code, 403)

    def test_staff_portal_accepts_django_staff_user(self):
        staff = self.create_user(email="staff@example.com", is_staff=True)
        self.client.force_login(staff)

        response = self.client.get(reverse("library:staff_portal"))

        self.assertEqual(response.status_code, 200)


class StaffCrudTests(LibraryTestCase):
    def setUp(self):
        self.staff = self.create_user(email="staff@example.com", is_staff=True)
        self.client.force_login(self.staff)

    def item_payload(self, **overrides):
        values = {
            "collection": LibraryItem.Collection.RESEARCH,
            "call_number": "RES-2026-101",
            "title": "New Research Resource",
            "author": "Research Team",
            "details": "A staff-managed resource.",
            "file_type": "PDF",
            "pages": 42,
            "publication_month": "2026-02",
            "publication_day": "14",
            "resource": SimpleUploadedFile(
                "research.pdf", b"%PDF-1.4 test resource", content_type="application/pdf"
            ),
        }
        values.update(overrides)
        return values

    def announcement_payload(self, **overrides):
        values = {
            "title": "Staff announcement",
            "body": "This announcement was created in the staff portal.",
            "category": Announcement.Category.GENERAL,
        }
        values.update(overrides)
        return values

    def test_staff_item_create_get_is_read_only_and_post_creates_item(self):
        url = reverse("library:staff_item_create")

        get_response = self.client.get(url)
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(LibraryItem.objects.count(), 0)

        post_response = self.client.post(url, self.item_payload())
        self.assertEqual(post_response.status_code, 302)
        item = LibraryItem.objects.get(call_number="RES-2026-101")
        self.assertEqual(item.title, "New Research Resource")
        self.assertEqual(item.created_by, self.staff)
        self.assertEqual(item.published_on.isoformat(), "2026-02-14")
        self.assertTrue(item.publication_day_known)

    def test_resource_accepts_word_file_and_month_without_day(self):
        response = self.client.post(
            reverse("library:staff_item_create"),
            self.item_payload(
                call_number="WORD-2026-001",
                file_type=LibraryItem.FileType.WORD,
                publication_month="2026-07",
                publication_day="",
                resource=SimpleUploadedFile(
                    "research.docx",
                    b"word document fixture",
                    content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ),
            ),
        )

        self.assertEqual(response.status_code, 302)
        item = LibraryItem.objects.get(call_number="WORD-2026-001")
        self.assertEqual(item.published_on.isoformat(), "2026-07-01")
        self.assertFalse(item.publication_day_known)
        self.assertEqual(item.publication_date_display, "July 2026")

    def test_resource_rejects_file_that_does_not_match_selected_format(self):
        response = self.client.post(
            reverse("library:staff_item_create"),
            self.item_payload(
                call_number="BAD-FORMAT-001",
                file_type=LibraryItem.FileType.WORD,
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "must match the selected PDF or Word format")
        self.assertFalse(LibraryItem.objects.filter(call_number="BAD-FORMAT-001").exists())
    def test_staff_item_edit_get_is_read_only_and_post_updates_item(self):
        item = self.create_item()
        url = reverse("library:staff_item_edit", args=[item.pk])

        get_response = self.client.get(url)
        self.assertEqual(get_response.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.title, "Django Testing Handbook")

        post_response = self.client.post(
            url, self.item_payload(call_number=item.call_number, title="Edited title")
        )
        self.assertEqual(post_response.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.title, "Edited title")

    def test_staff_item_delete_is_post_only(self):
        item = self.create_item()
        url = reverse("library:staff_item_delete", args=[item.pk])

        get_response = self.client.get(url)
        self.assertEqual(get_response.status_code, 405)
        self.assertTrue(LibraryItem.objects.filter(pk=item.pk).exists())

        post_response = self.client.post(url)
        self.assertEqual(post_response.status_code, 302)
        self.assertFalse(LibraryItem.objects.filter(pk=item.pk).exists())

    def test_staff_announcement_create_get_is_read_only_and_post_creates(self):
        url = reverse("library:staff_announcement_create")

        get_response = self.client.get(url)
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(Announcement.objects.count(), 0)

        post_response = self.client.post(url, self.announcement_payload())
        self.assertEqual(post_response.status_code, 302)
        announcement = Announcement.objects.get(title="Staff announcement")
        self.assertEqual(announcement.created_by, self.staff)
        self.assertEqual(
            post_response.url,
            f'{reverse("library:announcements")}#announcement-{announcement.pk}',
        )
        self.assertFalse(announcement.is_featured)
        self.assertFalse(announcement.is_published)
        self.assertIsNone(announcement.published_at)
        self.assertNotContains(get_response, "Is featured")
        self.assertNotContains(get_response, "Is published")

    def test_staff_can_publish_reviewed_draft_for_public_roles(self):
        create_response = self.client.post(
            reverse("library:staff_announcement_create"),
            self.announcement_payload(
                title="Publish after review",
                category=Announcement.Category.OTHER,
            ),
        )
        announcement = Announcement.objects.get(title="Publish after review")
        self.assertFalse(announcement.is_published)
        self.assertNotContains(
            self.client.get(reverse("library:announcements")),
            "Is published",
        )

        publish_response = self.client.post(
            reverse("library:staff_announcement_publish", args=[announcement.pk])
        )
        self.assertEqual(publish_response.status_code, 302)
        announcement.refresh_from_db()
        self.assertTrue(announcement.is_published)
        self.assertIsNotNone(announcement.published_at)

        self.client.logout()
        for role in ("guest", Profile.Role.STUDENT, Profile.Role.TEACHER):
            with self.subTest(role=role):
                if role != "guest":
                    self.client.force_login(
                        self.create_user(email=f"publish-{role}@example.com", role=role)
                    )
                response = self.client.get(reverse("library:announcements"))
                self.assertContains(response, announcement.title)
                self.client.logout()
    def test_staff_sees_draft_with_edit_and_delete_controls(self):
        draft = self.create_announcement(
            title="Administrator draft",
            is_published=False,
            published_at=None,
        )

        response = self.client.get(reverse("library:announcements"))

        self.assertContains(response, draft.title)
        self.assertContains(response, "Draft")
        self.assertContains(
            response, reverse("library:staff_announcement_edit", args=[draft.pk])
        )
        self.assertContains(
            response, reverse("library:staff_announcement_delete", args=[draft.pk])
        )
    def test_staff_announcement_edit_get_is_read_only_and_post_updates(self):
        announcement = self.create_announcement()
        url = reverse("library:staff_announcement_edit", args=[announcement.pk])

        get_response = self.client.get(url)
        self.assertEqual(get_response.status_code, 200)
        announcement.refresh_from_db()
        self.assertEqual(announcement.title, "Library update")

        post_response = self.client.post(
            url, self.announcement_payload(title="Edited announcement")
        )
        self.assertEqual(post_response.status_code, 302)
        announcement.refresh_from_db()
        self.assertEqual(announcement.title, "Edited announcement")

    def test_staff_announcement_delete_is_post_only(self):
        announcement = self.create_announcement()
        url = reverse("library:staff_announcement_delete", args=[announcement.pk])

        get_response = self.client.get(url)
        self.assertEqual(get_response.status_code, 405)
        self.assertTrue(Announcement.objects.filter(pk=announcement.pk).exists())

        post_response = self.client.post(url)
        self.assertEqual(post_response.status_code, 302)
        self.assertFalse(Announcement.objects.filter(pk=announcement.pk).exists())

    def test_staff_user_create_hashes_password_and_cannot_escalate_privileges(self):
        url = reverse("library:staff_user_create")

        get_response = self.client.get(url)
        self.assertEqual(get_response.status_code, 200)
        starting_count = get_user_model().objects.count()

        post_response = self.client.post(
            url,
            {
                "full_name": "New Teacher",
                "email": "new-teacher@example.com",
                "role": Profile.Role.TEACHER,
                "password1": TEST_PASSWORD,
                "password2": TEST_PASSWORD,
                # These unexpected fields must never grant privileges.
                "is_staff": "on",
                "is_superuser": "on",
            },
        )

        self.assertEqual(post_response.status_code, 302)
        self.assertEqual(get_user_model().objects.count(), starting_count + 1)
        user = get_user_model().objects.get(email="new-teacher@example.com")
        self.assertTrue(user.check_password(TEST_PASSWORD))
        self.assertNotEqual(user.password, TEST_PASSWORD)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.profile.role, Profile.Role.TEACHER)
        self.assertIsNone(user.profile.privacy_consent_accepted_at)
        self.assertEqual(user.profile.privacy_consent_version, "")

    def test_staff_user_create_rejects_administrator_role(self):
        response = self.client.post(
            reverse("library:staff_user_create"),
            {
                "full_name": "Unapproved Administrator",
                "email": "unapproved-admin@example.com",
                "role": "administrator",
                "password1": TEST_PASSWORD,
                "password2": TEST_PASSWORD,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            get_user_model()
            .objects.filter(email="unapproved-admin@example.com")
            .exists()
        )
