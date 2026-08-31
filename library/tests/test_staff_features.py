"""Regression coverage for staff filters, deletion, audit history, and analytics."""

from django.urls import reverse
from django.utils import timezone

from library.models import ActivityLog, Profile, WebsiteVisit
from library.tests.base import LibraryTestCase


class StaffManagementFeatureTests(LibraryTestCase):
    def setUp(self):
        self.staff = self.create_user(
            email="staff-features@example.com", is_staff=True
        )
        self.client.force_login(self.staff)

    def test_user_search_role_filter_and_created_sort(self):
        student = self.create_user(email="student-filter@example.com")
        teacher = self.create_user(
            email="teacher-filter@example.com", role=Profile.Role.TEACHER
        )

        response = self.client.get(
            reverse("library:staff_portal"),
            {"user_q": "teacher-filter", "user_role": "teacher", "user_sort": "oldest"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["users"]), [teacher])
        self.assertNotIn(student, response.context["users"])
        self.assertEqual(response.context["selected_user_sort"], "oldest")

    def test_staff_can_delete_reader_account_and_action_is_logged(self):
        reader = self.create_user(email="delete-reader@example.com")

        response = self.client.post(
            reverse("library:staff_user_delete", args=[reader.pk])
        )

        self.assertRedirects(response, reverse("library:staff_portal"))
        self.assertFalse(type(reader).objects.filter(pk=reader.pk).exists())
        self.assertTrue(
            ActivityLog.objects.filter(
                action=ActivityLog.Action.DELETE,
                object_type="user account",
                description="delete-reader@example.com",
                actor=self.staff,
            ).exists()
        )

    def test_current_and_superuser_accounts_are_protected_from_delete(self):
        response = self.client.post(
            reverse("library:staff_user_delete", args=[self.staff.pk])
        )
        self.assertRedirects(response, reverse("library:staff_portal"))
        self.assertTrue(type(self.staff).objects.filter(pk=self.staff.pk).exists())

        superuser = self.create_user(
            email="protected-root@example.com", is_staff=True, is_superuser=True
        )
        self.client.post(reverse("library:staff_user_delete", args=[superuser.pk]))
        self.assertTrue(type(superuser).objects.filter(pk=superuser.pk).exists())

    def test_usage_context_is_filtered_by_date_and_role(self):
        selected_date = timezone.localdate()
        WebsiteVisit.objects.create(
            session_key="teacher-session",
            user=None,
            role=WebsiteVisit.Role.TEACHER,
            duration_seconds=300,
        )

        response = self.client.get(
            reverse("library:staff_portal"),
            {"analytics_date": selected_date.isoformat()},
        )

        teacher_usage = next(
            row for row in response.context["role_usage"] if row["role"] == "teacher"
        )
        self.assertEqual(teacher_usage["minutes"], 5.0)
        self.assertContains(response, "Website usage")
        self.assertContains(response, "teacher-session", count=0)

class AIDetectionServiceTests(LibraryTestCase):
    def setUp(self):
        self.staff = self.create_user(
            email="ai-reviewer@example.com", is_staff=True
        )
        self.url = reverse("library:staff_ai_detection")

    def test_ai_detection_is_restricted_to_staff(self):
        anonymous_response = self.client.get(self.url)
        self.assertEqual(anonymous_response.status_code, 302)

        reader = self.create_user(email="ai-reader@example.com")
        self.client.force_login(reader)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_ai_detection_is_visible_in_staff_navigation_and_homepage(self):
        self.client.force_login(self.staff)

        page_response = self.client.get(self.url)
        portal_response = self.client.get(reverse("library:staff_portal"))

        self.assertEqual(page_response.status_code, 200)
        self.assertContains(page_response, "AI DETECTION")
        self.assertContains(portal_response, "AI Detection")
        self.assertContains(portal_response, self.url)

    def test_staff_can_analyze_pasted_text(self):
        self.client.force_login(self.staff)
        sample = (
            "Research supports careful evaluation of evidence and sources. "
            "Students should compare claims, identify limitations, and explain "
            "their reasoning before reaching a conclusion. This process helps "
            "readers understand how the evidence supports the final argument."
        )

        response = self.client.post(self.url, {"text": sample})

        self.assertEqual(response.status_code, 200)
        self.assertIn("detection_result", response.context)
        self.assertGreater(response.context["detection_result"]["word_count"], 20)
        self.assertContains(response, "Vocabulary diversity")
