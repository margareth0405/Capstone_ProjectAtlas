"""Regression coverage for staff filters, deletion, audit history, and analytics."""

from datetime import datetime, time, timedelta
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from docx import Document

from library.models import (
    ActivityLog,
    AIAnalysis,
    Profile,
    ResourceViewEvent,
    WebsiteVisit,
)
from library.services.staff_portal import StaffUserDirectory
from library.tests.base import TEST_PASSWORD, LibraryTestCase
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
        superuser = self.create_user(
            email="superuser-filter@example.com",
            is_staff=True,
            is_superuser=True,
        )

        response = self.client.get(
            reverse("library:staff_users"),
            {"user_q": "teacher-filter", "user_role": "teacher", "user_sort": "oldest"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["users"]), [teacher])
        self.assertNotIn(student, response.context["users"])
        self.assertEqual(response.context["selected_user_sort"], "oldest")
        account_totals = response.context["stats"]
        self.assertEqual(account_totals["total_users"], 4)
        self.assertEqual(account_totals["student_users"], 1)
        self.assertEqual(account_totals["teacher_users"], 1)
        self.assertEqual(account_totals["administrator_users"], 1)
        self.assertEqual(account_totals["superuser_users"], 1)
        self.assertContains(response, "All accounts")
        self.assertContains(response, "Students")
        self.assertContains(response, "Teachers")
        self.assertContains(response, "Administrators")
        self.assertContains(response, "Superusers")
        self.assertContains(response, '?user_role=student')
        self.assertContains(response, '?user_role=teacher')
        self.assertContains(response, '?user_role=administrator')
        self.assertContains(response, '?user_role=superuser')

        superuser_response = self.client.get(
            reverse("library:staff_users"),
            {"user_role": "superuser"},
        )
        self.assertEqual(list(superuser_response.context["users"]), [superuser])
        self.assertEqual(
            superuser_response.context["users"][0].atlas_role_label,
            "Superuser",
        )

        administrator_response = self.client.get(
            reverse("library:staff_users"),
            {"user_role": "administrator"},
        )
        self.assertEqual(
            list(administrator_response.context["users"]),
            [self.staff],
        )

    def test_user_directory_handles_account_without_profile(self):
        legacy_user = get_user_model()(
            username="legacy-without-profile@example.com",
            email="legacy-without-profile@example.com",
        )
        get_user_model().objects.bulk_create([legacy_user])

        response = self.client.get(reverse("library:staff_users"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "legacy-without-profile@example.com")
        self.assertContains(response, "Student")

        filtered_response = self.client.get(
            reverse("library:staff_users"),
            {"user_role": "student"},
        )
        self.assertContains(filtered_response, "legacy-without-profile@example.com")

    def test_account_page_presents_username_and_password_as_separate_actions(self):
        response = self.client.get(reverse("library:staff_account_edit"))

        self.assertContains(response, "These are two separate actions.")
        self.assertContains(response, "Change username")
        self.assertContains(response, "Change password")
        self.assertContains(response, 'name="account_action" value="username"')
        self.assertContains(response, 'name="account_action" value="password"')
        self.assertContains(response, 'id="id_username-current_password"')
        self.assertContains(response, 'id="id_password-current_password"')

    def test_staff_can_update_own_username_without_changing_password(self):
        response = self.client.post(
            reverse("library:staff_account_edit"),
            {
                "account_action": "username",
                "username-username": "updated-atlas-admin",
                "username-current_password": TEST_PASSWORD,
                # Password-looking values must be ignored by this action.
                "password-new_password1": "Ignored-Password-2026!",
                "password-new_password2": "Ignored-Password-2026!",
            },
        )

        self.assertRedirects(response, reverse("library:staff_account_edit"))
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.username, "updated-atlas-admin")
        self.assertTrue(self.staff.check_password(TEST_PASSWORD))
        self.assertIn("_auth_user_id", self.client.session)
        self.assertTrue(
            ActivityLog.objects.filter(
                actor=self.staff,
                action=ActivityLog.Action.UPDATE,
                object_type="administrator account",
                description="Username changed to updated-atlas-admin",
            ).exists()
        )

    def test_staff_can_change_own_password_without_changing_username(self):
        original_username = self.staff.username
        response = self.client.post(
            reverse("library:staff_account_edit"),
            {
                "account_action": "password",
                "password-current_password": TEST_PASSWORD,
                "password-new_password1": "New-Atlas-Admin-2026!",
                "password-new_password2": "New-Atlas-Admin-2026!",
                # Username-looking values must be ignored by this action.
                "username-username": "ignored-username",
            },
        )

        self.assertRedirects(response, reverse("library:staff_account_edit"))
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.username, original_username)
        self.assertTrue(self.staff.check_password("New-Atlas-Admin-2026!"))
        self.assertIn("_auth_user_id", self.client.session)
        self.assertTrue(
            ActivityLog.objects.filter(
                actor=self.staff,
                action=ActivityLog.Action.UPDATE,
                object_type="administrator account",
                description="Password changed",
            ).exists()
        )

    def test_staff_cannot_edit_another_administrator(self):
        other_admin = self.create_user(
            email="other-admin@example.com",
            is_staff=True,
        )

        response = self.client.get(
            reverse("library:staff_admin_edit", args=[other_admin.pk])
        )

        self.assertEqual(response.status_code, 403)

    def test_superuser_can_edit_another_administrator(self):
        superuser = self.create_user(
            email="root-admin@example.com",
            is_staff=True,
            is_superuser=True,
        )
        target = self.create_user(email="managed-admin@example.com", is_staff=True)
        self.client.force_login(superuser)

        response = self.client.post(
            reverse("library:staff_admin_edit", args=[target.pk]),
            {
                "account_action": "username",
                "username-username": "managed-admin",
                "username-current_password": TEST_PASSWORD,
            },
        )

        self.assertRedirects(
            response,
            reverse("library:staff_users"),
        )
        target.refresh_from_db()
        self.assertEqual(target.username, "managed-admin")

    def test_only_superuser_can_open_administrator_creation(self):
        url = reverse("library:superuser_admin_create")

        response = self.client.get(url)

        self.assertEqual(response.status_code, 403)
        response = self.client.post(
            url,
            {
                "full_name": "Unauthorized Administrator",
                "email": "unauthorized-admin@example.com",
                "username": "unauthorized-admin",
                "password1": "Unauthorized-Admin-2026!",
                "password2": "Unauthorized-Admin-2026!",
                "current_password": TEST_PASSWORD,
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            get_user_model()
            .objects.filter(email="unauthorized-admin@example.com")
            .exists()
        )
        users_page = self.client.get(reverse("library:staff_users"))
        self.assertNotContains(users_page, url)

        superuser = self.create_user(
            email="root-create-admin@example.com",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(superuser)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create an administrator account")
        self.assertContains(response, 'data-password-toggle="id_password1"')
        self.assertContains(response, 'data-password-toggle="id_password2"')
        self.assertContains(response, 'data-password-toggle="id_current_password"')
        self.assertContains(self.client.get(reverse("library:staff_users")), url)

    def test_superuser_can_create_regular_administrator(self):
        superuser = self.create_user(
            email="root-owner@example.com",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(superuser)

        response = self.client.post(
            reverse("library:superuser_admin_create"),
            {
                "full_name": "Second Administrator",
                "email": "second-admin@example.com",
                "username": "second-admin",
                "password1": "Quartz-Library-2026!",
                "password2": "Quartz-Library-2026!",
                "current_password": TEST_PASSWORD,
                # Unexpected privilege fields must never create another superuser.
                "is_staff": "on",
                "is_superuser": "on",
            },
        )

        self.assertRedirects(
            response,
            reverse("library:staff_users"),
        )
        administrator = get_user_model().objects.get(
            email="second-admin@example.com"
        )
        self.assertTrue(administrator.is_active)
        self.assertTrue(administrator.is_staff)
        self.assertFalse(administrator.is_superuser)
        self.assertTrue(administrator.check_password("Quartz-Library-2026!"))
        self.assertFalse(Profile.objects.filter(user=administrator).exists())
        self.assertTrue(
            EmailAddress.objects.filter(
                user=administrator,
                email=administrator.email,
                verified=True,
                primary=True,
            ).exists()
        )
        self.assertTrue(
            ActivityLog.objects.filter(
                actor=superuser,
                action=ActivityLog.Action.CREATE,
                object_type="administrator account",
                object_id=str(administrator.pk),
            ).exists()
        )

        self.client.logout()
        self.assertTrue(
            self.client.login(
                username="second-admin",
                password="Quartz-Library-2026!",
            )
        )
        self.assertEqual(
            self.client.get(reverse("library:staff_portal")).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(reverse("library:superuser_admin_create")).status_code,
            403,
        )

    def test_administrator_creation_requires_superuser_password(self):
        superuser = self.create_user(
            email="root-password-check@example.com",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(superuser)

        response = self.client.post(
            reverse("library:superuser_admin_create"),
            {
                "full_name": "Blocked Administrator",
                "email": "blocked-admin@example.com",
                "username": "blocked-admin",
                "password1": "Blocked-Admin-2026!",
                "password2": "Blocked-Admin-2026!",
                "current_password": "incorrect-password",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Superuser password is incorrect")
        self.assertFalse(
            get_user_model()
            .objects.filter(email="blocked-admin@example.com")
            .exists()
        )

    def test_user_directory_falls_back_when_optional_join_fails(self):
        fallback_accounts = [self.staff]

        with patch.object(
            StaffUserDirectory,
            "build",
            side_effect=[
                DatabaseError("resource-view relation unavailable"),
                fallback_accounts,
            ],
        ):
            response = self.client.get(reverse("library:staff_users"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["users"], fallback_accounts)
        self.assertContains(response, self.staff.email)

    def test_staff_reports_survive_unavailable_optional_history_tables(self):
        with (
            patch(
                "library.services.staff_portal.ResourceViewEvent.objects.count",
                side_effect=DatabaseError("resource-view count unavailable"),
            ),
            patch(
                "library.services.staff_portal.ResourceViewDirectory.build",
                side_effect=DatabaseError("resource-view history unavailable"),
            ),
            patch(
                "library.services.staff_portal.UsageAnalytics.role_usage",
                side_effect=DatabaseError("usage analytics unavailable"),
            ),
            patch(
                "library.services.staff_portal.ActivityLog.objects.select_related",
                side_effect=DatabaseError("activity history unavailable"),
            ),
        ):
            response = self.client.get(reverse("library:staff_reports"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["resource_view_count"], 0)
        self.assertEqual(response.context["resource_view_history"], [])
        self.assertEqual(response.context["activity_history"], [])
        self.assertEqual(response.context["visit_history"], [])
        self.assertEqual(response.context["usage_summary"]["sessions"], 0)

    def test_staff_reports_render_guest_visit_and_null_activity_actor(self):
        WebsiteVisit.objects.create(
            session_key="anonymous-dashboard-visit",
            user=None,
            role=WebsiteVisit.Role.GUEST,
            duration_seconds=45,
            page_views=1,
            last_path="/repository/",
        )
        ActivityLog.objects.create(
            actor=None,
            action=ActivityLog.Action.UPDATE,
            object_type="system task",
            description="Automated maintenance",
        )

        response = self.client.get(reverse("library:staff_reports"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Guest visitor")
        self.assertContains(response, "Automated maintenance")
        self.assertContains(response, "System")

    def test_audit_trail_filters_action_and_inclusive_date_range(self):
        created_entry = ActivityLog.objects.create(
            actor=self.staff,
            action=ActivityLog.Action.CREATE,
            object_type="repository resource",
            description="Created outside selected action",
        )
        updated_entry = ActivityLog.objects.create(
            actor=self.staff,
            action=ActivityLog.Action.UPDATE,
            object_type="repository resource",
            description="Updated inside selected date",
        )
        deleted_entry = ActivityLog.objects.create(
            actor=self.staff,
            action=ActivityLog.Action.DELETE,
            object_type="repository resource",
            description="Deleted outside selected date",
        )
        current_timezone = timezone.get_current_timezone()
        ActivityLog.objects.filter(pk=created_entry.pk).update(
            occurred_at=datetime(2026, 9, 15, 9, 0, tzinfo=current_timezone)
        )
        ActivityLog.objects.filter(pk=updated_entry.pk).update(
            occurred_at=datetime(2026, 9, 15, 23, 59, tzinfo=current_timezone)
        )
        ActivityLog.objects.filter(pk=deleted_entry.pk).update(
            occurred_at=datetime(2026, 9, 16, 9, 0, tzinfo=current_timezone)
        )

        response = self.client.get(
            reverse("library:staff_reports"),
            {
                "audit_action": ActivityLog.Action.UPDATE,
                "audit_start_date": "2026-09-15",
                "audit_end_date": "2026-09-15",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["activity_history"], [updated_entry])
        self.assertEqual(response.context["selected_audit_action"], "update")
        self.assertEqual(response.context["audit_history_count"], 1)
        self.assertContains(response, "Updated inside selected date")
        self.assertNotContains(response, "Created outside selected action")
        self.assertNotContains(response, "Deleted outside selected date")

    def test_audit_trail_rejects_reversed_date_range(self):
        ActivityLog.objects.create(
            actor=self.staff,
            action=ActivityLog.Action.CREATE,
            object_type="repository resource",
            description="Hidden while the date range is invalid",
        )

        response = self.client.get(
            reverse("library:staff_reports"),
            {
                "audit_start_date": "2026-09-20",
                "audit_end_date": "2026-09-10",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["activity_history"], [])
        self.assertContains(
            response,
            "The start date must be on or before the end date.",
        )

    def test_audit_filters_use_mobile_friendly_native_controls(self):
        response = self.client.get(reverse("library:staff_reports"))

        self.assertContains(response, 'class="audit-filter-form"')
        self.assertContains(response, 'type="date" name="audit_start_date"')
        self.assertContains(response, 'type="date" name="audit_end_date"')
        self.assertContains(response, "Apply filters")
        self.assertContains(response, "Created")
        self.assertContains(response, "Updated")
        self.assertContains(response, "Deleted")

    def test_staff_can_delete_reader_account_and_action_is_logged(self):
        reader = self.create_user(email="delete-reader@example.com")

        response = self.client.post(
            reverse("library:staff_user_delete", args=[reader.pk])
        )

        self.assertRedirects(
            response,
            reverse("library:staff_users"),
        )
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
        self.assertRedirects(
            response,
            reverse("library:staff_users"),
        )
        self.assertTrue(type(self.staff).objects.filter(pk=self.staff.pk).exists())

        superuser = self.create_user(
            email="protected-root@example.com", is_staff=True, is_superuser=True
        )
        self.client.post(reverse("library:staff_user_delete", args=[superuser.pk]))
        self.assertTrue(type(superuser).objects.filter(pk=superuser.pk).exists())

        other_admin = self.create_user(
            email="protected-admin@example.com",
            is_staff=True,
        )
        self.client.post(reverse("library:staff_user_delete", args=[other_admin.pk]))
        self.assertTrue(type(other_admin).objects.filter(pk=other_admin.pk).exists())

    def test_account_delete_database_failure_rolls_back_without_500(self):
        reader = self.create_user(email="rollback-delete@example.com")

        with patch(
            "library.views.staff_accounts.ActivityRecorder.record",
            side_effect=DatabaseError("activity table unavailable"),
        ):
            response = self.client.post(
                reverse("library:staff_user_delete", args=[reader.pk]),
                follow=True,
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No changes were saved")
        self.assertTrue(type(reader).objects.filter(pk=reader.pk).exists())

    def test_usage_context_is_filtered_by_date_and_role(self):
        selected_date = timezone.localdate()
        WebsiteVisit.objects.create(
            session_key="teacher-session",
            user=None,
            role=WebsiteVisit.Role.TEACHER,
            duration_seconds=300,
        )

        response = self.client.get(
            reverse("library:staff_reports"),
            {"analytics_date": selected_date.isoformat()},
        )

        teacher_usage = next(
            row for row in response.context["role_usage"] if row["role"] == "teacher"
        )
        self.assertEqual(teacher_usage["minutes"], 5.0)
        self.assertEqual(teacher_usage["percent"], 100.0)
        self.assertEqual(response.context["usage_percentage_basis"], "Active time")
        self.assertContains(response, "Website usage")
        self.assertContains(response, "100.0% active time")
        self.assertContains(response, "teacher-session", count=0)


class WebsiteUsageRegressionTests(LibraryTestCase):
    def setUp(self):
        self.staff = self.create_user(
            email="usage-staff@example.com", is_staff=True
        )
        self.client.force_login(self.staff)
        self.client.cookies["atlas_cookie_consent"] = "analytics"

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
            reverse("library:staff_reports"),
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
        self.assertFalse(WebsiteVisit.objects.filter(user=self.staff).exists())

        page_view_response = self.client.post(
            reverse("library:usage_heartbeat"),
            {"event": "page_view", "path": dashboard_url},
        )
        self.assertEqual(page_view_response.status_code, 204)
        visit = WebsiteVisit.objects.get(user=self.staff)
        visit.refresh_from_db()
        self.assertEqual(visit.page_views, 1)
        self.assertEqual(visit.last_path, dashboard_url)

        self.client.get(dashboard_url)
        self.client.post(
            reverse("library:usage_heartbeat"),
            {"event": "page_view", "path": dashboard_url},
        )
        self.client.post(
            reverse("library:usage_heartbeat"),
            {"event": "heartbeat", "path": dashboard_url},
        )
        visit.refresh_from_db()
        self.assertEqual(visit.page_views, 1)

    def test_visitors_count_distinct_guest_sessions_and_signed_in_users(self):
        WebsiteVisit.objects.create(
            session_key="same-guest",
            user=None,
            role=WebsiteVisit.Role.GUEST,
        )
        WebsiteVisit.objects.create(
            session_key="same-guest",
            user=None,
            role=WebsiteVisit.Role.GUEST,
        )
        reader = self.create_user(email="unique-reader@example.com")
        WebsiteVisit.objects.create(
            session_key="reader-one",
            user=reader,
            role=WebsiteVisit.Role.STUDENT,
        )
        WebsiteVisit.objects.create(
            session_key="reader-two",
            user=reader,
            role=WebsiteVisit.Role.STUDENT,
        )

        response = self.client.get(reverse("library:staff_reports"))

        self.assertEqual(response.context["usage_summary"]["sessions"], 4)
        self.assertEqual(response.context["usage_summary"]["visitors"], 2)

    def test_new_visits_use_session_share_until_active_time_is_recorded(self):
        WebsiteVisit.objects.create(
            session_key="student-fresh-one",
            user=None,
            role=WebsiteVisit.Role.STUDENT,
        )
        WebsiteVisit.objects.create(
            session_key="student-fresh-two",
            user=None,
            role=WebsiteVisit.Role.STUDENT,
        )
        WebsiteVisit.objects.create(
            session_key="teacher-fresh",
            user=None,
            role=WebsiteVisit.Role.TEACHER,
        )

        response = self.client.get(reverse("library:staff_reports"))
        role_usage = {row["role"]: row for row in response.context["role_usage"]}

        self.assertEqual(response.context["usage_percentage_basis"], "Sessions")
        self.assertEqual(role_usage[WebsiteVisit.Role.STUDENT]["percent"], 66.7)
        self.assertEqual(role_usage[WebsiteVisit.Role.TEACHER]["percent"], 33.3)
        self.assertContains(response, "66.7% sessions")

    def test_empty_usage_dashboard_explains_analytics_consent(self):
        response = self.client.get(reverse("library:staff_reports"))

        self.assertFalse(response.context["has_usage_activity"])
        self.assertContains(response, "No website usage activity recorded")
        self.assertContains(response, "Signed-in account activity is recorded automatically")
        self.assertContains(response, "Review analytics preference")

    def test_visit_history_search_and_account_type_filter(self):
        teacher = self.create_user(
            email="find-this-teacher@example.com",
            role=Profile.Role.TEACHER,
        )
        teacher_visit = WebsiteVisit.objects.create(
            session_key="teacher-filter-session",
            user=teacher,
            role=WebsiteVisit.Role.TEACHER,
        )
        WebsiteVisit.objects.create(
            session_key="guest-filter-session",
            user=None,
            role=WebsiteVisit.Role.GUEST,
        )

        response = self.client.get(
            reverse("library:staff_reports"),
            {"usage_q": "find-this", "usage_role": WebsiteVisit.Role.TEACHER},
        )

        self.assertEqual(list(response.context["visit_history"]), [teacher_visit])
        self.assertContains(response, teacher_visit.display_name)
        self.assertContains(response, 'value="find-this"')
        self.assertContains(response, 'name="usage_role"')

    def test_resource_view_history_can_filter_by_role_and_resource(self):
        teacher = self.create_user(
            email="resource-teacher@example.com",
            role=Profile.Role.TEACHER,
        )
        item = self.create_item(title="Filtered Atlas Resource")
        event = ResourceViewEvent.objects.create(
            item=item,
            user=teacher,
            session_key="resource-filter-session",
            role=WebsiteVisit.Role.TEACHER,
        )

        response = self.client.get(
            reverse("library:staff_reports"),
            {
                "resource_view_q": "Filtered Atlas",
                "resource_view_role": WebsiteVisit.Role.TEACHER,
            },
        )

        self.assertEqual(list(response.context["resource_view_history"]), [event])
        self.assertContains(response, "Resource viewing history")
        self.assertNotContains(response, "Download history")
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

    class StubAnalyzer:
        def analyze(self, text):
            return {
                "score": 76.5,
                "label": "High AI-pattern score",
                "tone": "high",
                "ai_probability": 76.5,
                "human_probability": 23.5,
                "confidence": 76.5,
                "chunks_analyzed": 2,
                "detector_name": "Desklib Academic AI Text Detector",
                "model_name": "desklib/ai-text-detector-academic-v1.01",
                "model_version": "test-commit-123",
            }

    def test_ai_detection_is_restricted_to_staff_and_teachers(self):
        anonymous_response = self.client.get(self.url)
        self.assertEqual(anonymous_response.status_code, 302)

        reader = self.create_user(email="ai-reader@example.com")
        self.client.force_login(reader)
        self.assertEqual(self.client.get(self.url).status_code, 403)

        teacher = self.create_user(
            email="ai-teacher@deped.gov.ph",
            role=Profile.Role.TEACHER,
        )
        self.client.force_login(teacher)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_ai_detection_is_visible_in_staff_navigation_and_homepage(self):
        self.client.force_login(self.staff)

        page_response = self.client.get(self.url)
        portal_response = self.client.get(reverse("library:staff_portal"))

        self.assertEqual(page_response.status_code, 200)
        self.assertContains(page_response, "AI DETECTION")
        self.assertContains(page_response, "PDF")
        self.assertContains(page_response, "Word (.docx)")
        self.assertContains(page_response, "up to 25 MB")
        self.assertContains(page_response, 'enctype="multipart/form-data"')
        self.assertContains(page_response, "data-async-upload")
        self.assertContains(page_response, "data-exclusive-ai-inputs")
        self.assertContains(page_response, "Selecting a document clears pasted text")
        self.assertContains(page_response, "ATLAS is analyzing the writing patterns")
        self.assertContains(page_response, 'class="ai-input-grid"')
        self.assertContains(page_response, 'class="staff-panel ai-detection-form-card"')
        self.assertContains(page_response, 'class="staff-panel ai-detection-result-card"')
        self.assertContains(portal_response, "AI Detection")
        self.assertContains(portal_response, self.url)
        self.assertContains(
            portal_response,
            f'class="admin-function-card" href="{self.url}"',
        )
        self.assertNotContains(portal_response, 'class="staff-panel staff-ai-entry"')

    def test_ai_result_styles_keep_scores_inside_cards_on_narrow_screens(self):
        stylesheet = (
            Path(settings.BASE_DIR)
            / "library"
            / "static"
            / "library"
            / "css"
            / "theme"
            / "administrator.css"
        ).read_text(encoding="utf-8")

        self.assertIn("font-size: clamp(1.65rem, 7vw, 2.2rem);", stylesheet)
        self.assertIn("font-variant-numeric: tabular-nums;", stylesheet)
        self.assertIn("overflow-wrap: anywhere;", stylesheet)
        self.assertIn(".ai-metrics .ai-metric-version", stylesheet)
        self.assertIn("grid-column: span 3;", stylesheet)
        self.assertIn("word-break: break-all;", stylesheet)
        self.assertIn("@media (max-width: 520px)", stylesheet)

    def test_staff_can_analyze_pasted_text(self):
        self.client.force_login(self.staff)
        sample = (
            "Research supports careful evaluation of evidence and sources. "
            "Students should compare claims, identify limitations, and explain "
            "their reasoning before reaching a conclusion. This process helps "
            "readers understand how the evidence supports the final argument."
        )

        with patch.object(
            StaffAIDetectionView,
            "analyzer_class",
            self.StubAnalyzer,
        ):
            response = self.client.post(self.url, {"text": sample})

        self.assertEqual(response.status_code, 200)
        self.assertIn("detection_result", response.context)
        self.assertEqual(
            response.context["detection_result"]["ai_probability"],
            76.5,
        )
        self.assertContains(response, "AI-pattern score")
        self.assertContains(response, "Human-pattern score")
        self.assertContains(response, "Desklib Academic AI Text Detector")
        self.assertContains(response, 'class="ai-metric-version"')
        self.assertContains(response, 'title="test-commit-123"')
        self.assertContains(response, "not proof")
        analysis = AIAnalysis.objects.get(reviewer=self.staff)
        self.assertEqual(analysis.source_name, "Pasted text")
        self.assertEqual(analysis.model_version, "test-commit-123")
        self.assertEqual(float(analysis.ai_probability), 76.5)

    def test_benchmark_result_can_render_desklib_and_vanguard_metadata(self):
        self.client.force_login(self.staff)
        sample = "Academic evidence should be interpreted in context. " * 5

        class ComparingAnalyzer(self.StubAnalyzer):
            def analyze(self, text):
                primary = super().analyze(text)
                result = dict(primary)
                result.update(
                    {
                        "primary": primary,
                        "comparison_complete": True,
                        "detectors_disagree": False,
                        "score_difference": 4.5,
                        "comparison_status": (
                            "Both models are on the AI-pattern side of the 50% "
                            "threshold."
                        ),
                        "comparison": {
                            "score": 72.0,
                            "label": "High AI-pattern score",
                            "tone": "high",
                            "ai_probability": 72.0,
                            "human_probability": 28.0,
                            "confidence": 72.0,
                            "chunks_analyzed": 2,
                            "detector_name": "Vanguard AI Text Detector",
                            "model_name": "ShantanuT01/vanguard-ai-text-detector",
                            "model_version": "vanguard-test-commit",
                        },
                    }
                )
                return result

        with patch.object(
            StaffAIDetectionView,
            "analyzer_class",
            ComparingAnalyzer,
        ):
            response = self.client.post(self.url, {"text": sample})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Desklib result")
        self.assertContains(response, "Vanguard result")
        self.assertContains(response, "Models agree at the 50% threshold")
        self.assertContains(response, "4.5 percentage-point difference")
        analysis = AIAnalysis.objects.get(reviewer=self.staff)
        self.assertEqual(
            analysis.comparison_result["model_name"],
            "ShantanuT01/vanguard-ai-text-detector",
        )

    def test_staff_sees_inconclusive_when_models_disagree(self):
        self.client.force_login(self.staff)
        sample = "Academic evidence should be interpreted in context. " * 5

        class DisagreeingAnalyzer(self.StubAnalyzer):
            def analyze(self, text):
                primary = super().analyze(text)
                result = dict(primary)
                result.update(
                    {
                        "label": "Inconclusive — models disagree",
                        "tone": "mixed",
                        "primary": primary,
                        "comparison_complete": True,
                        "detectors_disagree": True,
                        "score_difference": 54.5,
                        "comparison_status": (
                            "The models fall on opposite sides of the 50% "
                            "screening threshold."
                        ),
                        "comparison": {
                            "score": 22.0,
                            "label": "Low AI-pattern score",
                            "tone": "low",
                            "ai_probability": 22.0,
                            "human_probability": 78.0,
                            "confidence": 78.0,
                            "chunks_analyzed": 2,
                            "detector_name": "Vanguard AI Text Detector",
                            "model_name": "ShantanuT01/vanguard-ai-text-detector",
                            "model_version": "vanguard-test-commit",
                        },
                    }
                )
                return result

        with patch.object(
            StaffAIDetectionView,
            "analyzer_class",
            DisagreeingAnalyzer,
        ):
            response = self.client.post(self.url, {"text": sample})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Inconclusive — models disagree")
        self.assertContains(response, "opposite sides")

    @override_settings(AI_DETECTION_ENGINE="fast")
    def test_fast_engine_completes_real_text_request(self):
        self.client.force_login(self.staff)
        sample = (
            "A research claim needs evidence from more than one source. "
            "The writer should compare the methods, discuss conflicting results, "
            "and explain the limitations before drawing a conclusion. "
        ) * 3

        response = self.client.post(self.url, {"text": sample})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["detection_result"]["detector_name"],
            "ATLAS Fast Pattern Review",
        )
        self.assertTrue(AIAnalysis.objects.filter(reviewer=self.staff).exists())

    def test_analysis_result_survives_history_database_failure(self):
        self.client.force_login(self.staff)
        sample = "Evidence should be compared and explained carefully. " * 5

        with (
            patch.object(
                StaffAIDetectionView,
                "analyzer_class",
                self.StubAnalyzer,
            ),
            patch.object(
                AIAnalysis,
                "record",
                side_effect=DatabaseError("analysis table unavailable"),
            ),
        ):
            response = self.client.post(self.url, {"text": sample})

        self.assertEqual(response.status_code, 200)
        self.assertIn("detection_result", response.context)
        self.assertContains(response, "Analysis completed")
        self.assertContains(response, "database migrations")

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

        with patch.object(
            StaffAIDetectionView,
            "analyzer_class",
            self.StubAnalyzer,
        ):
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
        ), patch.object(
            StaffAIDetectionView,
            "analyzer_class",
            self.StubAnalyzer,
        ):
            response = self.client.post(self.url, {"document": upload})

        self.assertEqual(response.status_code, 200)
        self.assertIn("detection_result", response.context)
        self.assertEqual(response.context["detection_source"], "research-paper.pdf")
