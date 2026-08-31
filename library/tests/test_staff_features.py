"""Regression coverage for staff filters, deletion, audit history, and analytics."""

from datetime import datetime, time, timedelta
from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from docx import Document

from library.models import ActivityLog, Profile, WebsiteVisit
from library.tests.base import LibraryTestCase
from library.views.staff_ai import StaffAIDetectionView


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


class WebsiteUsageRegressionTests(LibraryTestCase):
    def setUp(self):
        self.staff = self.create_user(
            email="usage-staff@example.com", is_staff=True
        )
        self.client.force_login(self.staff)

    def test_historical_usage_date_excludes_todays_visits(self):
        historical_date = timezone.localdate() - timedelta(days=7)
        historical_visit = WebsiteVisit.objects.create(
            session_key="historical-session",
            user=None,
            role=WebsiteVisit.Role.STUDENT,
            duration_seconds=180,
            page_views=4,
            last_path="/catalog/",
        )
        historical_started_at = timezone.make_aware(
            datetime.combine(historical_date, time(hour=10))
        )
        WebsiteVisit.objects.filter(pk=historical_visit.pk).update(
            started_at=historical_started_at,
            last_seen_at=historical_started_at + timedelta(minutes=3),
        )
        WebsiteVisit.objects.create(
            session_key="today-session",
            user=None,
            role=WebsiteVisit.Role.TEACHER,
            duration_seconds=600,
            page_views=20,
        )

        response = self.client.get(
            reverse("library:staff_portal"),
            {"analytics_date": historical_date.isoformat()},
        )

        self.assertEqual(response.context["analytics_date"], historical_date.isoformat())
        self.assertEqual(response.context["usage_summary"]["sessions"], 1)
        self.assertEqual(response.context["usage_summary"]["page_views"], 4)
        self.assertEqual(list(response.context["visit_history"]), [historical_visit])
        self.assertContains(response, f'value="{historical_date.isoformat()}"')

    def test_refresh_request_does_not_add_a_page_view(self):
        dashboard_url = reverse("library:dashboard")
        self.client.get(dashboard_url)
        visit = WebsiteVisit.objects.get(user=self.staff)
        self.assertEqual(visit.page_views, 0)

        page_view_response = self.client.post(
            reverse("library:usage_heartbeat"),
            {"event": "page_view", "path": dashboard_url},
        )
        self.assertEqual(page_view_response.status_code, 204)
        visit.refresh_from_db()
        self.assertEqual(visit.page_views, 1)
        self.assertEqual(visit.last_path, dashboard_url)

        self.client.get(dashboard_url)
        self.client.post(
            reverse("library:usage_heartbeat"),
            {"event": "heartbeat", "path": dashboard_url},
        )
        visit.refresh_from_db()
        self.assertEqual(visit.page_views, 1)

    def test_usage_event_rejects_external_style_path(self):
        response = self.client.post(
            reverse("library:usage_heartbeat"),
            {"event": "page_view", "path": "//example.com/not-atlas"},
        )
        self.assertEqual(response.status_code, 400)

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
        self.assertContains(page_response, "PDF")
        self.assertContains(page_response, "Word (.docx)")
        self.assertContains(page_response, 'enctype="multipart/form-data"')
        self.assertContains(page_response, 'class="ai-input-grid"')
        self.assertContains(page_response, 'class="staff-panel ai-detection-form-card"')
        self.assertContains(page_response, 'class="staff-panel ai-detection-result-card"')
        self.assertContains(portal_response, "AI Detection")
        self.assertContains(portal_response, self.url)
        self.assertContains(portal_response, 'class="staff-panel staff-ai-entry"')
        self.assertNotContains(portal_response, 'class="staff-service-card"')

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
    def test_staff_can_analyze_word_document_without_saving_it(self):
        self.client.force_login(self.staff)
        document = Document()
        document.add_paragraph(
            "Research writing should explain evidence carefully and compare "
            "multiple reliable sources. Students need to identify limitations, "
            "connect each claim to supporting information, and communicate the "
            "reasoning that leads to a conclusion. These steps make an academic "
            "argument easier for readers to examine and understand."
        )
        stream = BytesIO()
        document.save(stream)
        upload = SimpleUploadedFile(
            "research-review.docx",
            stream.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        response = self.client.post(self.url, {"document": upload})

        self.assertEqual(response.status_code, 200)
        self.assertIn("detection_result", response.context)
        self.assertEqual(response.context["detection_source"], "research-review.docx")
        self.assertContains(response, "research-review.docx")

    def test_ai_detection_rejects_unsupported_file_type(self):
        self.client.force_login(self.staff)
        upload = SimpleUploadedFile(
            "notes.txt",
            b"This unsupported text file contains enough content for validation.",
            content_type="text/plain",
        )

        response = self.client.post(self.url, {"document": upload})

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("detection_result", response.context)
        self.assertContains(response, "Upload a PDF or Word (.docx) document.")
    def test_staff_can_submit_pdf_to_document_extractor(self):
        self.client.force_login(self.staff)
        upload = SimpleUploadedFile(
            "research-paper.pdf",
            b"%PDF-1.4 test fixture",
            content_type="application/pdf",
        )

        class StubPdfExtractor:
            def extract(self, uploaded_file):
                self.received_name = uploaded_file.name
                return (
                    "A PDF document can provide enough extracted academic text "
                    "for the writing pattern analyzer to calculate vocabulary "
                    "diversity and sentence variation. This test confirms that "
                    "the administrator upload workflow sends PDF input through "
                    "the configured document extraction service correctly."
                )

        with patch.object(
            StaffAIDetectionView,
            "extractor_class",
            StubPdfExtractor,
        ):
            response = self.client.post(self.url, {"document": upload})

        self.assertEqual(response.status_code, 200)
        self.assertIn("detection_result", response.context)
        self.assertEqual(response.context["detection_source"], "research-paper.pdf")
