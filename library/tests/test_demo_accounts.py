import os
from io import StringIO
from typing import ClassVar
from unittest.mock import patch

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from library.forms import AtlasAdminAuthenticationForm, RoleLoginForm
from library.models import Profile


@override_settings(
    PRIVACY_CONSENT_VERSION="demo-consent-2026",
    TEACHER_EMAIL_DOMAINS=("deped.gov.ph",),
)
class ProvisionDemoAccountsCommandTests(TestCase):
    environment: ClassVar[dict[str, str]] = {
        "ATLAS_PROVISION_DEMO_ACCOUNTS": "True",
        "ATLAS_DEMO_STUDENT_EMAIL": "student@atlas.edu",
        "ATLAS_DEMO_STUDENT_NAME": "Demo Student",
        "ATLAS_DEMO_STUDENT_PASSWORD": "Jade!River7-Student-92",
        "ATLAS_DEMO_TEACHER_EMAIL": "teacher@deped.gov.ph",
        "ATLAS_DEMO_TEACHER_NAME": "Demo Teacher",
        "ATLAS_DEMO_TEACHER_PASSWORD": "Copper!Sky8-Teacher-41",
        "ATLAS_DEMO_ADMIN_USERNAME": "atlas_demo_admin",
        "ATLAS_DEMO_ADMIN_EMAIL": "demo.administrator@example.com",
        "ATLAS_DEMO_ADMIN_NAME": "Demo Administrator",
        "ATLAS_DEMO_ADMIN_PASSWORD": "Quartz!Lake6-Admin-73",
        "ATLAS_DEMO_SUPERUSER_USERNAME": "atlas_demo_superuser",
        "ATLAS_DEMO_SUPERUSER_EMAIL": "demo.superuser@example.com",
        "ATLAS_DEMO_SUPERUSER_NAME": "Demo Superuser",
        "ATLAS_DEMO_SUPERUSER_PASSWORD": "Maple!Cloud5-Super-84",
    }

    def run_command(self, environment=None):
        output = StringIO()
        with patch.dict(os.environ, environment or self.environment, clear=False):
            call_command("provision_demo_accounts", stdout=output)
        return output.getvalue()

    def test_disabled_command_does_not_change_accounts(self):
        output = self.run_command({"ATLAS_PROVISION_DEMO_ACCOUNTS": "False"})

        self.assertEqual(get_user_model().objects.count(), 0)
        self.assertIn("disabled", output)

    def test_creates_verified_role_aware_accounts_that_can_sign_in(self):
        output = self.run_command()

        User = get_user_model()
        self.assertEqual(User.objects.count(), 4)
        self.assertIn("4 created, 0 updated", output)

        student = User.objects.get(username="student@atlas.edu")
        self.assertFalse(student.is_staff)
        self.assertFalse(student.is_superuser)
        self.assertEqual(student.profile.role, Profile.Role.STUDENT)
        self.assertEqual(
            student.profile.privacy_consent_version,
            "demo-consent-2026",
        )
        self.assertIsNotNone(student.profile.privacy_consent_accepted_at)
        self.assertEqual(student.profile.age_consent_version, "demo-consent-2026")
        self.assertIsNotNone(student.profile.age_consent_confirmed_at)

        teacher = User.objects.get(username="teacher@deped.gov.ph")
        self.assertEqual(teacher.profile.role, Profile.Role.TEACHER)

        administrator = User.objects.get(username="atlas_demo_admin")
        self.assertTrue(administrator.is_staff)
        self.assertFalse(administrator.is_superuser)

        superuser = User.objects.get(username="atlas_demo_superuser")
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)

        self.assertEqual(
            EmailAddress.objects.filter(verified=True, primary=True).count(),
            4,
        )
        self.assertTrue(
            RoleLoginForm(
                data={
                    "email": student.email,
                    "password": self.environment["ATLAS_DEMO_STUDENT_PASSWORD"],
                    "role": Profile.Role.STUDENT,
                    "privacy_consent": True,
                }
            ).is_valid()
        )
        self.assertTrue(
            RoleLoginForm(
                data={
                    "email": teacher.email,
                    "password": self.environment["ATLAS_DEMO_TEACHER_PASSWORD"],
                    "role": Profile.Role.TEACHER,
                    "privacy_consent": True,
                }
            ).is_valid()
        )
        self.assertTrue(
            AtlasAdminAuthenticationForm(
                request=None,
                data={
                    "username": administrator.email,
                    "password": self.environment["ATLAS_DEMO_ADMIN_PASSWORD"],
                },
            ).is_valid()
        )
        self.assertTrue(
            AtlasAdminAuthenticationForm(
                request=None,
                data={
                    "username": superuser.username,
                    "password": self.environment["ATLAS_DEMO_SUPERUSER_PASSWORD"],
                },
            ).is_valid()
        )

    def test_rerun_updates_passwords_without_duplicate_accounts(self):
        self.run_command()
        User = get_user_model()
        original_ids = set(User.objects.values_list("pk", flat=True))
        changed_environment = {
            **self.environment,
            "ATLAS_DEMO_STUDENT_PASSWORD": "Amber!Field4-Student-68",
        }

        output = self.run_command(changed_environment)

        self.assertEqual(set(User.objects.values_list("pk", flat=True)), original_ids)
        self.assertIn("0 created, 4 updated", output)
        student = User.objects.get(username="student@atlas.edu")
        self.assertTrue(student.check_password("Amber!Field4-Student-68"))

    def test_missing_password_stops_before_any_account_is_created(self):
        incomplete_environment = {
            **self.environment,
            "ATLAS_DEMO_TEACHER_PASSWORD": "",
        }

        with (
            patch.dict(os.environ, incomplete_environment, clear=False),
            self.assertRaisesMessage(
                CommandError,
                "Set ATLAS_DEMO_TEACHER_PASSWORD",
            ),
        ):
            call_command("provision_demo_accounts")

        self.assertEqual(get_user_model().objects.count(), 0)

    def test_teacher_email_must_follow_the_configured_domain_policy(self):
        invalid_environment = {
            **self.environment,
            "ATLAS_DEMO_TEACHER_EMAIL": "teacher@example.com",
        }

        with (
            patch.dict(os.environ, invalid_environment, clear=False),
            self.assertRaisesMessage(CommandError, "@deped.gov.ph"),
        ):
            call_command("provision_demo_accounts")

        self.assertEqual(get_user_model().objects.count(), 0)
