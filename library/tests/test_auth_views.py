"""Registration, login, session, and consent behavior."""

import smtplib
from io import StringIO
from unittest.mock import patch
from urllib.parse import urlsplit

from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core import mail
from django.core.management import call_command
from django.urls import reverse

from library.models import Profile

from .base import TEST_PASSWORD, LibraryTestCase


class RegistrationTests(LibraryTestCase):
    def registration_payload(self, **overrides):
        values = {
            "full_name": "Jamie Atlas",
            "email": "jamie@gmail.com",
            "role": Profile.Role.STUDENT,
            "password1": TEST_PASSWORD,
            "password2": TEST_PASSWORD,
            "age_consent": "on",
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
        self.assertIsNotNone(user.profile.age_consent_confirmed_at)
        self.assertEqual(
            user.profile.age_consent_version,
            settings.PRIVACY_CONSENT_VERSION,
        )
        self.assertEqual(
            user.profile.privacy_consent_version,
            settings.PRIVACY_CONSENT_VERSION,
        )
        email_address = EmailAddress.objects.get(user=user)
        self.assertEqual(email_address.email, "jamie@gmail.com")
        self.assertTrue(email_address.primary)

    @patch(
        "library.views.authentication.complete_signup",
        side_effect=smtplib.SMTPServerDisconnected("Connection unexpectedly closed"),
    )
    def test_registration_handles_smtp_disconnect_without_leaving_account(self, _signup):
        response = self.client.post(
            reverse("library:register"), self.registration_payload()
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "could not send the verification email")
        self.assertFalse(
            get_user_model().objects.filter(email="jamie@gmail.com").exists()
        )

    def test_allauth_signup_cannot_bypass_role_and_privacy_form(self):
        response = self.client.post(
            reverse("account_signup"),
            {
                "email": "bypass@example.com",
                "password1": TEST_PASSWORD,
                "password2": TEST_PASSWORD,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("library:register"))
        self.assertFalse(
            get_user_model().objects.filter(email="bypass@example.com").exists()
        )

    def test_registration_sends_and_accepts_email_verification(self):
        self.client.post(reverse("library:register"), self.registration_payload())
        self.assertIn("does not subscribe you to marketing email", mail.outbox[0].body)
        self.assertIn("request_type=email_preferences", mail.outbox[0].body)
        email_address = EmailAddress.objects.get(email="jamie@gmail.com")
        confirmation = EmailConfirmationHMAC(email_address)
        confirmation_url = reverse(
            "account_confirm_email", kwargs={"key": confirmation.key}
        )

        page_response = self.client.get(confirmation_url)
        self.assertEqual(page_response.status_code, 200)
        self.assertTemplateUsed(page_response, "account/email_confirm.html")
        self.assertContains(page_response, "Confirm your email")

        response = self.client.post(confirmation_url)
        self.assertEqual(response.status_code, 302)
        email_address.refresh_from_db()
        self.assertTrue(email_address.verified)

    def test_unverified_user_can_resend_verification_email(self):
        user = self.create_user(email="unverified@example.com")
        EmailAddress.objects.create(
            user=user,
            email=user.email,
            primary=True,
            verified=False,
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("account_email"),
            {"email": user.email, "action_send": ""},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Verify your ATLAS email address", mail.outbox[0].subject)

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

    def test_teacher_registration_rejects_non_deped_email(self):
        response = self.client.post(
            reverse("library:register"),
            self.registration_payload(
                email="teacher@gmail.com", role=Profile.Role.TEACHER
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Teacher accounts must use an official @deped.gov.ph email address.",
        )
        self.assertFalse(
            get_user_model().objects.filter(email="teacher@gmail.com").exists()
        )

    def test_registration_requires_privacy_consent(self):
        payload = self.registration_payload()
        payload.pop("privacy_consent")

        response = self.client.post(reverse("library:register"), payload)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            get_user_model().objects.filter(email="jamie@gmail.com").exists()
        )

    def test_registration_requires_minor_or_guardian_confirmation(self):
        payload = self.registration_payload()
        payload.pop("age_consent")

        response = self.client.post(reverse("library:register"), payload)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "age_consent")
        self.assertFalse(
            get_user_model().objects.filter(email="jamie@gmail.com").exists()
        )

    def test_registration_enforces_each_password_requirement(self):
        cases = (
            ("Aa1!", "This password is too short. It must contain at least 6 characters."),
            ("Atlas!", "Your password must contain at least one number."),
            ("Atlas1", "Your password must contain at least one special character."),
        )

        for index, (password, expected_error) in enumerate(cases):
            with self.subTest(password=password):
                email = f"password-check-{index}@example.com"
                response = self.client.post(
                    reverse("library:register"),
                    self.registration_payload(
                        email=email,
                        password1=password,
                        password2=password,
                    ),
                )

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, expected_error)
                self.assertFalse(
                    get_user_model().objects.filter(email=email).exists()
                )

    def test_registration_accepts_six_character_password_at_boundary(self):
        password = "Aa1!bc"

        response = self.client.post(
            reverse("library:register"),
            self.registration_payload(
                email="six-character@example.com",
                password1=password,
                password2=password,
            ),
        )

        self.assertEqual(response.status_code, 302)
        user = get_user_model().objects.get(email="six-character@example.com")
        self.assertTrue(user.check_password(password))

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
        EmailAddress.objects.create(
            user=self.user,
            email=self.user.email,
            primary=True,
            verified=True,
        )

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

    @patch(
        "library.views.authentication.perform_login",
        side_effect=smtplib.SMTPServerDisconnected("Connection unexpectedly closed"),
    )
    def test_login_handles_verification_email_disconnect(self, _login):
        response = self.client.post(
            reverse("library:login"),
            {
                "email": self.user.email,
                "password": TEST_PASSWORD,
                "role": Profile.Role.STUDENT,
                "privacy_consent": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "could not send the verification email")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_teacher_login_rejects_legacy_non_deped_account(self):
        teacher = self.create_user(
            email="legacy-teacher@gmail.com",
            role=Profile.Role.TEACHER,
        )

        response = self.client.post(
            reverse("library:login"),
            {
                "email": teacher.email,
                "password": TEST_PASSWORD,
                "role": Profile.Role.TEACHER,
                "privacy_consent": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Teacher accounts must use an official @deped.gov.ph email address.",
        )
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_explains_six_character_minimum(self):
        response = self.client.post(
            reverse("library:login"),
            {
                "email": self.user.email,
                "password": "A1!",
                "role": Profile.Role.STUDENT,
                "privacy_consent": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Your password must be at least 6 characters long.",
        )
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_uses_clear_incorrect_credentials_message(self):
        response = self.client.post(
            reverse("library:login"),
            {
                "email": self.user.email,
                "password": "Wrong1!",
                "role": Profile.Role.STUDENT,
                "privacy_consent": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Incorrect email or password. Check your details and try again.",
        )
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_dashboard_redirects_anonymous_users_to_login(self):
        response = self.client.get(reverse("library:dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("library:login"), response.url)

    def test_allauth_password_reset_is_available(self):
        response = self.client.get(reverse("account_reset_password"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account/password_reset.html")
        self.assertContains(response, "Reset your password")

    def test_allauth_password_reset_sends_recovery_email(self):
        response = self.client.post(
            reverse("account_reset_password"), {"email": self.user.email}
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.user.email, mail.outbox[0].to)

    def test_allauth_password_reset_link_changes_password(self):
        self.client.post(
            reverse("account_reset_password"), {"email": self.user.email}
        )
        reset_url = next(
            line.strip()
            for line in mail.outbox[0].body.splitlines()
            if "/accounts/password/reset/key/" in line
        )

        token_response = self.client.get(urlsplit(reset_url).path)
        self.assertEqual(token_response.status_code, 302)
        form_response = self.client.get(token_response.url)
        self.assertEqual(form_response.status_code, 200)
        self.assertTemplateUsed(
            form_response, "account/password_reset_from_key.html"
        )

        new_password = "New-Atlas-Pass-2026!"
        response = self.client.post(
            token_response.url,
            {"password1": new_password, "password2": new_password},
        )
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))

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
class WelcomeGreetingTests(LibraryTestCase):
    def test_greeting_prefers_non_email_username(self):
        user = self.create_user(email="reader@example.com")
        user.username = "atlas_reader"
        user.save(update_fields=("username",))
        self.client.force_login(user)

        response = self.client.get(reverse("library:dashboard"))

        self.assertEqual(response.context["display_name"], "atlas_reader")
        self.assertContains(response, "atlas_reader")
        self.assertNotContains(response, "reader@example.com")

    def test_email_shaped_username_never_exposes_full_email_in_greeting(self):
        user = self.create_user(email="quiet.reader@example.com")
        user.first_name = ""
        user.last_name = ""
        user.save(update_fields=("first_name", "last_name"))
        self.client.force_login(user)

        response = self.client.get(reverse("library:dashboard"))

        self.assertEqual(response.context["display_name"], "quiet.reader")
        self.assertContains(response, "quiet.reader")
        self.assertNotContains(response, "quiet.reader@example.com")
