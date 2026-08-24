"""Registration, login, session, and consent behavior."""

from io import StringIO

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.management import call_command
from django.urls import reverse

from library.models import Profile

from .base import LibraryTestCase, TEST_PASSWORD


class RegistrationTests(LibraryTestCase):
    def registration_payload(self, **overrides):
        values = {
            "full_name": "Jamie Atlas",
            "email": "jamie@gmail.com",
            "role": Profile.Role.STUDENT,
            "password1": TEST_PASSWORD,
            "password2": TEST_PASSWORD,
            "privacy_consent": "on",
        }
        values.update(overrides)
        return values

    def test_registration_creates_builtin_user_with_hashed_password_and_profile(self):
        response = self.client.post(
            reverse("library:register"), self.registration_payload()
        )

        self.assertEqual(response.status_code, 302)
        user = get_user_model().objects.get(email="jamie@gmail.com")
        self.assertNotEqual(user.password, TEST_PASSWORD)
        self.assertTrue(user.check_password(TEST_PASSWORD))
        self.assertEqual(user.profile.role, Profile.Role.STUDENT)
        self.assertIsNotNone(user.profile.privacy_consent_accepted_at)
        self.assertEqual(
            user.profile.privacy_consent_version,
            settings.PRIVACY_CONSENT_VERSION,
        )

    def test_teacher_registration_records_teacher_role(self):
        response = self.client.post(
            reverse("library:register"),
            self.registration_payload(
                email="teacher@deped.gov.ph", role=Profile.Role.TEACHER
            ),
        )

        self.assertEqual(response.status_code, 302)
        user = get_user_model().objects.get(email="teacher@deped.gov.ph")
        self.assertEqual(user.profile.role, Profile.Role.TEACHER)
        self.assertFalse(user.is_staff)

    def test_registration_requires_privacy_consent(self):
        payload = self.registration_payload()
        payload.pop("privacy_consent")

        response = self.client.post(reverse("library:register"), payload)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            get_user_model().objects.filter(email="jamie@gmail.com").exists()
        )

    def test_public_registration_cannot_create_an_administrator(self):
        response = self.client.post(
            reverse("library:register"),
            self.registration_payload(role="administrator"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            get_user_model().objects.filter(email="jamie@gmail.com").exists()
        )


class SeedCommandTests(LibraryTestCase):
    def test_seed_command_never_creates_an_administrator(self):
        call_command("seed_atlas", stdout=StringIO())

        users = get_user_model().objects.all()
        self.assertFalse(users.filter(is_staff=True).exists())
        self.assertFalse(users.filter(is_superuser=True).exists())
        self.assertTrue(users.filter(email="teacher@deped.gov.ph").exists())


class LoginAndSessionTests(LibraryTestCase):
    def setUp(self):
        self.user = self.create_user(email="reader@example.com")

    def test_login_requires_privacy_consent(self):
        response = self.client.post(
            reverse("library:login"),
            {
                "email": self.user.email,
                "password": TEST_PASSWORD,
                "role": Profile.Role.STUDENT,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.user.profile.refresh_from_db()
        self.assertIsNone(self.user.profile.privacy_consent_accepted_at)

    def test_successful_login_uses_django_session_and_records_current_consent(self):
        response = self.client.post(
            reverse("library:login"),
            {
                "email": self.user.email,
                "password": TEST_PASSWORD,
                "role": Profile.Role.STUDENT,
                "privacy_consent": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)
        self.user.profile.refresh_from_db()
        self.assertIsNotNone(self.user.profile.privacy_consent_accepted_at)
        self.assertEqual(
            self.user.profile.privacy_consent_version,
            settings.PRIVACY_CONSENT_VERSION,
        )

    def test_dashboard_redirects_anonymous_users_to_login(self):
        response = self.client.get(reverse("library:dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("library:login"), response.url)

    def test_dashboard_is_available_to_authenticated_users(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("library:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertNotIsInstance(response.wsgi_request.user, AnonymousUser)

    def test_logout_is_post_only_and_clears_the_django_session(self):
        self.client.force_login(self.user)

        get_response = self.client.get(reverse("library:logout"))
        self.assertEqual(get_response.status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)

        post_response = self.client.post(reverse("library:logout"))
        self.assertEqual(post_response.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)
