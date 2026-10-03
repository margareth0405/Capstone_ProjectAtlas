import os
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import TestCase

from library.models import Profile


class CreateLoadTestUsersCommandTests(TestCase):
    password = "AtlasLoadTest123!"

    def run_command(self, **options):
        output = StringIO()
        with patch.dict(
            os.environ,
            {"ATLAS_LOAD_TEST_PASSWORD": self.password},
            clear=False,
        ):
            call_command(
                "create_load_test_users",
                stdout=output,
                **options,
            )
        return output.getvalue()

    def test_creates_numbered_verified_student_accounts(self):
        output = self.run_command(count=2, prefix="loadcase", email_domain="example.com")

        User = get_user_model()
        users = User.objects.filter(username__startswith="loadcase").order_by("username")
        self.assertEqual(users.count(), 2)
        self.assertEqual(users[0].email, "loadcase001@example.com")
        self.assertTrue(users[0].check_password(self.password))
        self.assertEqual(users[0].profile.role, Profile.Role.STUDENT)
        self.assertIsNotNone(users[0].profile.privacy_consent_accepted_at)
        self.assertEqual(
            users[0].profile.privacy_consent_version,
            settings.PRIVACY_CONSENT_VERSION,
        )
        self.assertIsNotNone(users[0].profile.age_consent_confirmed_at)
        self.assertEqual(
            users[0].profile.age_consent_version,
            settings.PRIVACY_CONSENT_VERSION,
        )
        self.assertTrue(
            EmailAddress.objects.filter(
                user=users[0],
                email=users[0].email,
                verified=True,
                primary=True,
            ).exists()
        )
        self.assertIn("2 created, 0 updated", output)

    def test_rerun_updates_accounts_without_duplicates(self):
        self.run_command(count=2, prefix="loadcase", email_domain="example.com")
        output = self.run_command(
            count=2,
            prefix="loadcase",
            email_domain="example.com",
        )

        User = get_user_model()
        self.assertEqual(User.objects.filter(username__startswith="loadcase").count(), 2)
        self.assertIn("0 created, 2 updated", output)

    def test_requires_a_strong_environment_password(self):
        with (
            patch.dict(
                os.environ,
                {"ATLAS_LOAD_TEST_PASSWORD": "short"},
                clear=False,
            ),
            self.assertRaisesMessage(CommandError, "at least 12 characters"),
        ):
            call_command("create_load_test_users", count=1)

    def test_teacher_pool_requires_deped_domain(self):
        with (
            patch.dict(
                os.environ,
                {"ATLAS_LOAD_TEST_PASSWORD": self.password},
                clear=False,
            ),
            self.assertRaisesMessage(CommandError, "deped.gov.ph"),
        ):
            call_command(
                "create_load_test_users",
                count=1,
                role=Profile.Role.TEACHER,
                email_domain="example.com",
            )

    def test_authenticated_scenario_preserves_each_student_session(self):
        script = (
            Path(settings.BASE_DIR) / "load_tests" / "atlas-authenticated-test.js"
        ).read_text(encoding="utf-8")

        self.assertIn("noCookiesReset: true", script)
        self.assertIn("if (!authenticated)", script)
        self.assertIn("REAUTHENTICATE_EACH_ITERATION", script)
