"""Presentation contracts for role-based and administrator sign-in pages."""

import re
from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.urls import reverse

from library.models import DownloadEvent, Profile

from .base import TEST_PASSWORD, LibraryTestCase


class ReaderAuthPresentationTests(LibraryTestCase):
    def test_landing_role_links_preserve_student_and_teacher_selection(self):
        response = self.client.get(reverse("library:landing"))
        register_url = reverse("library:register")

        self.assertContains(response, f'href="{register_url}?role=student"')
        self.assertContains(response, f'href="{register_url}?role=teacher"')
        self.assertContains(response, "Already have an account?")
        self.assertContains(response, f'href="{reverse("library:login")}">Sign in</a>')

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

    def test_login_pages_show_role_choices_and_keep_role_in_hidden_field(self):
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
                self.assertContains(response, reverse("account_reset_password"))
                self.assertNotContains(response, "reader-role-toggle")
                self.assertNotContains(response, "role-selection-note")
                self.assertNotContains(response, "toggle-btn")

    def test_register_pages_show_role_choices_and_keep_role_in_hidden_field(self):
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

    def test_login_and_registration_offer_password_visibility_controls(self):
        login_response = self.client.get(reverse("library:login"))
        register_response = self.client.get(reverse("library:register"))

        self.assertContains(login_response, 'class="auth-role-switch"')
        self.assertContains(login_response, 'data-password-toggle="id_password"')
        self.assertContains(register_response, 'class="auth-role-switch"')
        self.assertContains(register_response, 'data-password-toggle="id_password1"')
        self.assertContains(register_response, 'data-password-toggle="id_password2"')
        self.assertContains(login_response, "data-protect-credentials")
        self.assertContains(register_response, "data-protect-credentials")
        self.assertContains(login_response, "data-sensitive-credential", count=2)
        self.assertContains(register_response, "data-sensitive-credential", count=4)
        self.assertContains(login_response, "Copy, cut, paste")
        self.assertContains(register_response, "Copy, cut, paste")
        self.assertContains(login_response, f'{reverse("library:login")}?role=student')
        self.assertContains(login_response, f'{reverse("library:login")}?role=teacher')
        self.assertNotContains(login_response, reverse("admin:login"))
        self.assertContains(register_response, f'{reverse("library:register")}?role=student')
        self.assertContains(register_response, f'{reverse("library:register")}?role=teacher')

    def test_registration_shows_live_password_checklist_and_strength(self):
        response = self.client.get(reverse("library:register"))

        self.assertContains(response, 'minlength="12"', count=2)
        self.assertContains(response, "At least 12 characters")
        self.assertContains(response, 'data-password-rule="length"')
        self.assertContains(response, 'data-password-rule="number"')
        self.assertContains(response, 'data-password-rule="special"')
        self.assertContains(
            response,
            "At least one symbol or punctuation character (any one is accepted)",
        )
        self.assertContains(response, 'data-password-rule="match"')
        self.assertContains(response, 'data-password-strength')
        self.assertContains(response, 'aria-label="Password strength"')
        self.assertContains(response, "data-single-submit")
        self.assertContains(response, 'data-submit-label="Registering…"')
        self.assertNotContains(response, "Example format: 12+ characters")

    def test_login_clearly_explains_legacy_and_new_password_rules(self):
        response = self.client.get(reverse("library:login"))

        self.assertContains(response, "Previously created passwords still work")
        self.assertContains(response, "at least 12 characters")

    def test_password_feedback_uses_an_encapsulated_controller(self):
        script = (
            Path(settings.BASE_DIR)
            / "library"
            / "static"
            / "library"
            / "js"
            / "app.js"
        ).read_text(encoding="utf-8")

        self.assertIn("class PasswordFeedback", script)
        self.assertIn('special: /[^\\p{L}\\p{N}\\s]/u.test(password)', script)
        self.assertIn('this.updateRule("match"', script)

    def test_consent_information_is_collapsed_behind_review_controls(self):
        login = self.client.get(reverse("library:login"))
        registration = self.client.get(reverse("library:register"))
        contact = self.client.get(reverse("library:contact"))

        self.assertContains(login, 'class="consent-disclosure"')
        self.assertContains(login, "Review privacy agreement")
        self.assertContains(login, "<strong>Yes</strong>", html=True)
        self.assertContains(registration, 'class="consent-disclosure"', count=2)
        self.assertContains(registration, "Review age and guardian confirmation")
        self.assertContains(registration, "Review privacy agreement")
        self.assertContains(contact, 'class="consent-disclosure"')
        self.assertContains(contact, "Review message privacy agreement")

    def test_every_password_input_can_receive_a_visibility_toggle(self):
        script = (
            Path(settings.BASE_DIR)
            / "library"
            / "static"
            / "library"
            / "js"
            / "app.js"
        ).read_text(encoding="utf-8")

        self.assertIn('querySelectorAll(\'input[type="password"]\')', script)
        self.assertIn('input.type = show ? "text" : "password"', script)
        self.assertIn('show ? "Hide password" : "Show password"', script)

        template_expectations = {
            "templates/account/password_reset_from_key.html": (
                "id_password1",
                "id_password2",
            ),
            "templates/account/password_change.html": ("data-password-toggle",),
            "templates/account/password_set.html": ("data-password-toggle",),
            "templates/library/admin/user_form.html": ("data-password-toggle",),
            "templates/library/admin/account_form.html": ("data-password-toggle",),
            "templates/library/admin/administrator_form.html": (
                "data-password-toggle",
            ),
        }
        for relative_path, expected_markers in template_expectations.items():
            with self.subTest(template=relative_path):
                template = (Path(settings.BASE_DIR) / relative_path).read_text(
                    encoding="utf-8"
                )
                self.assertIn("password-field", template)
                for marker in expected_markers:
                    self.assertIn(marker, template)

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
    def test_legacy_download_history_is_registered_read_only(self):
        model_admin = admin.site._registry[DownloadEvent]

        self.assertFalse(model_admin.has_add_permission(None))
        self.assertFalse(model_admin.has_change_permission(None))
        self.assertFalse(model_admin.has_delete_permission(None))

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
        self.assertContains(response, 'class="auth-role-switch"')
        self.assertNotContains(response, "Administrator")
        self.assertContains(
            response,
            '<input type="hidden" name="role" value="student">',
            html=True,
        )
        self.assertNotContains(
            response,
            '<input type="hidden" name="role" value="administrator">',
            html=True,
        )

    def test_landing_does_not_expose_administrator_login(self):
        response = self.client.get(reverse("library:landing"))

        self.assertNotContains(response, reverse("admin:login"))
        self.assertNotContains(response, reverse("library:staff_portal"))
        self.assertNotContains(response, "Administrator sign in")

    def test_django_admin_uses_configured_private_path(self):
        self.assertEqual(reverse("admin:index"), f"/{settings.ADMIN_URL_PATH}/")
        self.assertEqual(
            reverse("admin:login"), f"/{settings.ADMIN_URL_PATH}/login/"
        )

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

    def test_createsuperuser_account_accepts_username_or_email(self):
        superuser = get_user_model().objects.create_superuser(
            username="atlas-root",
            email="root-login@example.com",
            password=TEST_PASSWORD,
        )

        for identifier in (superuser.get_username(), superuser.email):
            with self.subTest(identifier=identifier):
                self.client.logout()
                response = self.client.post(
                    reverse("admin:login"),
                    {
                        "username": identifier,
                        "password": TEST_PASSWORD,
                        "next": reverse("library:staff_portal"),
                    },
                )

                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.url, reverse("library:staff_portal"))
                self.assertEqual(
                    int(self.client.session["_auth_user_id"]), superuser.pk
                )

    def test_administrator_and_superuser_land_on_custom_staff_home(self):
        accounts = (
            self.create_user(email="landing-admin@example.com", is_staff=True),
            self.create_user(
                email="landing-superuser@example.com",
                is_staff=True,
                is_superuser=True,
            ),
        )

        for account in accounts:
            with self.subTest(account=account.email):
                self.client.logout()
                response = self.client.post(
                    reverse("admin:login"),
                    {
                        "username": account.get_username(),
                        "password": TEST_PASSWORD,
                    },
                )
                self.assertRedirects(
                    response,
                    reverse("library:staff_portal"),
                    fetch_redirect_response=False,
                )

                admin_index = self.client.get(reverse("admin:index"))
                self.assertRedirects(
                    admin_index,
                    reverse("library:staff_portal"),
                    fetch_redirect_response=False,
                )

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
        self.assertEqual(response.url, reverse("library:staff_portal"))


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
            Path(settings.BASE_DIR) / "library" / "static" / "library" / "css" / "django.css"
        ).read_text(encoding="utf-8")
        body_rule = self._last_rule(css, "body")

        self.assertRegex(body_rule, r"(?m)^\s*height\s*:\s*auto\s*;")
        self.assertRegex(body_rule, r"(?m)^\s*overflow-y\s*:\s*auto\s*;")
        self.assertNotRegex(body_rule, r"(?m)^\s*overflow\s*:\s*hidden\s*;")

    def test_dashboard_containers_do_not_trap_vertical_scrolling(self):
        css = (
            Path(settings.BASE_DIR) / "library" / "static" / "library" / "css" / "django.css"
        ).read_text(encoding="utf-8")

        for selector in (".atlas-shell", ".main-content", ".django-view"):
            with self.subTest(selector=selector):
                rule = self._last_rule(css, selector)
                self.assertRegex(rule, r"(?m)^\s*overflow\s*:\s*visible\s*;")
                self.assertNotRegex(rule, r"(?m)^\s*overflow\s*:\s*hidden\s*;")

    def test_dashboard_sidebar_can_resize_without_splitting_words(self):
        project_root = Path(settings.BASE_DIR)
        template = (project_root / "templates/library/dashboard_base.html").read_text(
            encoding="utf-8"
        )
        styles = (
            project_root / "library/static/library/css/theme/style.css"
        ).read_text(encoding="utf-8")
        responsive_styles = (
            project_root / "library/static/library/css/theme/responsive.css"
        ).read_text(encoding="utf-8")
        script = (project_root / "library/static/library/js/app.js").read_text(
            encoding="utf-8"
        )

        self.assertIn('data-sidebar-resize', template)
        self.assertIn('role="separator"', template)
        self.assertIn("--sidebar-min-width: 17.5rem", styles)
        self.assertIn(".sidebar-resize-handle", styles)
        self.assertIn("overflow-wrap: normal", responsive_styles)
        self.assertIn('var sidebarStorageKey = "atlas_sidebar_width"', script)
        self.assertIn('event.key === "ArrowLeft"', script)
        self.assertIn('event.key === "ArrowRight"', script)
