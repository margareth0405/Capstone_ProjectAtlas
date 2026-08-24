"""Presentation contracts for role-based and administrator sign-in pages."""

import re
from pathlib import Path

from django.conf import settings
from django.urls import reverse

from library.models import Profile

from .base import LibraryTestCase, TEST_PASSWORD


class ReaderAuthPresentationTests(LibraryTestCase):
    def test_landing_role_links_preserve_student_and_teacher_selection(self):
        response = self.client.get(reverse("library:landing"))
        login_url = reverse("library:login")

        self.assertContains(response, f'href="{login_url}?role=student"')
        self.assertContains(response, f'href="{login_url}?role=teacher"')

    def test_landing_role_buttons_do_not_render_subtitles(self):
        response = self.client.get(reverse("library:landing"))

        self.assertContains(response, "Student")
        self.assertContains(response, "Teacher")
        self.assertContains(response, "Guest")
        for subtitle in (
            "Read, download, and save favorites",
            "Access the teaching and reading collection",
            "Browse public resources as a visitor",
        ):
            with self.subTest(subtitle=subtitle):
                self.assertNotContains(response, subtitle)

    def test_login_pages_have_no_role_toggle_and_keep_role_in_hidden_field(self):
        for role, heading in (
            (Profile.Role.STUDENT, "Student Login"),
            (Profile.Role.TEACHER, "Teacher Login"),
        ):
            with self.subTest(role=role):
                response = self.client.get(
                    reverse("library:login"), {"role": role}
                )

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, heading)
                self.assertContains(
                    response,
                    f'<input type="hidden" name="role" value="{role}">',
                    html=True,
                )
                self.assertContains(
                    response,
                    f'{reverse("library:register")}?role={role}',
                )
                self.assertNotContains(response, "reader-role-toggle")
                self.assertNotContains(response, "role-selection-note")
                self.assertNotContains(response, "toggle-btn")

    def test_register_pages_have_no_role_toggle_and_keep_role_in_hidden_field(self):
        for role, heading in (
            (Profile.Role.STUDENT, "Student Registration"),
            (Profile.Role.TEACHER, "Teacher Registration"),
        ):
            with self.subTest(role=role):
                response = self.client.get(
                    reverse("library:register"), {"role": role}
                )

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, heading)
                self.assertContains(
                    response,
                    f'<input type="hidden" name="role" value="{role}">',
                    html=True,
                )
                self.assertContains(
                    response,
                    f'{reverse("library:login")}?role={role}',
                )
                self.assertNotContains(response, "reader-role-toggle")
                self.assertNotContains(response, "role-selection-note")
                self.assertNotContains(response, "toggle-btn")

    def test_invalid_teacher_login_post_preserves_hidden_role(self):
        response = self.client.post(
            reverse("library:login"),
            {
                "email": "teacher@deped.gov.ph",
                "password": "incorrect-password",
                "role": Profile.Role.TEACHER,
                "privacy_consent": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Teacher Login")
        self.assertContains(
            response,
            '<input type="hidden" name="role" value="teacher">',
            html=True,
        )
        self.assertNotContains(response, "reader-role-toggle")

    def test_invalid_teacher_registration_post_preserves_hidden_role(self):
        response = self.client.post(
            reverse("library:register"),
            {
                "full_name": "Teacher Atlas",
                "email": "teacher@deped.gov.ph",
                "role": Profile.Role.TEACHER,
                "password1": TEST_PASSWORD,
                "password2": "does-not-match",
                "privacy_consent": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Teacher Registration")
        self.assertContains(
            response,
            '<input type="hidden" name="role" value="teacher">',
            html=True,
        )
        self.assertNotContains(response, "reader-role-toggle")


class AtlasAdminLoginTests(LibraryTestCase):
    def test_public_pages_do_not_expose_administrator_entry_points(self):
        public_requests = (
            (reverse("library:landing"), None),
            (reverse("library:login"), {"role": "administrator"}),
            (reverse("library:register"), {"role": "administrator"}),
            (reverse("library:catalog"), None),
            (reverse("library:announcements"), None),
            (reverse("library:contact"), None),
        )

        for url, query in public_requests:
            with self.subTest(url=url):
                response = self.client.get(url, query or {})
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, reverse("admin:login"))
                self.assertNotContains(response, reverse("library:staff_portal"))

    def test_public_login_cannot_select_administrator_role(self):
        response = self.client.get(
            reverse("library:login"), {"role": "administrator"}
        )

        self.assertContains(response, "Student Login")
        self.assertNotContains(response, "Administrator")
        self.assertContains(
            response,
            '<input type="hidden" name="role" value="student">',
            html=True,
        )

    def test_landing_does_not_expose_administrator_login(self):
        response = self.client.get(reverse("library:landing"))

        self.assertNotContains(response, reverse("admin:login"))
        self.assertNotContains(response, reverse("library:staff_portal"))
        self.assertNotContains(response, "Administrator sign in")

    def test_django_admin_uses_configured_private_path(self):
        self.assertEqual(reverse("admin:index"), f"/{settings.ADMIN_URL_PATH}/")

    def test_robots_does_not_disclose_private_admin_path(self):
        response = self.client.get(reverse("library:robots_txt"))

        self.assertNotContains(response, settings.ADMIN_URL_PATH)

    def test_django_admin_login_uses_atlas_auth_page_theme(self):
        response = self.client.get(reverse("admin:login"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin/login.html")
        self.assertContains(response, "atlas-auth-page")
        self.assertContains(response, "login-container")
        self.assertContains(response, "login-card")
        self.assertContains(response, "Administrator Login")
        self.assertContains(
            response,
            '<meta name="robots" content="noindex, nofollow">',
            html=True,
        )
        self.assertContains(response, "Skip to main content")
        self.assertContains(response, "Email or username")

    def test_staff_user_can_sign_in_through_django_admin_login(self):
        staff = self.create_user(email="staff-login@example.com", is_staff=True)

        response = self.client.post(
            reverse("admin:login"),
            {
                "username": staff.get_username(),
                "password": TEST_PASSWORD,
                "next": reverse("admin:index"),
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("admin:index"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), staff.pk)

    def test_nonstaff_user_is_rejected_by_django_admin_login(self):
        nonstaff = self.create_user(email="reader-login@example.com")

        response = self.client.post(
            reverse("admin:login"),
            {
                "username": nonstaff.get_username(),
                "password": TEST_PASSWORD,
                "next": reverse("admin:index"),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertContains(response, "staff account")

    def test_authenticated_staff_is_redirected_away_from_admin_login(self):
        staff = self.create_user(email="signed-in-staff@example.com", is_staff=True)
        self.client.force_login(staff)

        response = self.client.get(reverse("admin:login"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("admin:index"))


class ScrollingStyleTests(LibraryTestCase):
    @staticmethod
    def _last_rule(css, selector):
        matches = tuple(
            re.finditer(
                rf"(?:^|\}})\s*{re.escape(selector)}\s*\{{(?P<body>.*?)\}}",
                css,
                flags=re.MULTILINE | re.DOTALL,
            )
        )
        if not matches:
            raise AssertionError(f"Missing CSS rule for {selector}")
        return matches[-1].group("body")

    def test_integration_styles_restore_document_scrolling(self):
        css = (
            Path(settings.BASE_DIR) / "static" / "library" / "css" / "django.css"
        ).read_text(encoding="utf-8")
        body_rule = self._last_rule(css, "body")

        self.assertRegex(body_rule, r"(?m)^\s*height\s*:\s*auto\s*;")
        self.assertRegex(body_rule, r"(?m)^\s*overflow-y\s*:\s*auto\s*;")
        self.assertNotRegex(body_rule, r"(?m)^\s*overflow\s*:\s*hidden\s*;")

    def test_dashboard_containers_do_not_trap_vertical_scrolling(self):
        css = (
            Path(settings.BASE_DIR) / "static" / "library" / "css" / "django.css"
        ).read_text(encoding="utf-8")

        for selector in (".atlas-shell", ".main-content", ".django-view"):
            with self.subTest(selector=selector):
                rule = self._last_rule(css, selector)
                self.assertRegex(rule, r"(?m)^\s*overflow\s*:\s*visible\s*;")
                self.assertNotRegex(rule, r"(?m)^\s*overflow\s*:\s*hidden\s*;")
