"""Create verified, non-staff ATLAS accounts for authorized load testing."""

import os

from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from library.models import Profile


class Command(BaseCommand):
    help = (
        "Idempotently create a numbered pool of verified ATLAS load-test users. "
        "The shared password is read from an environment variable."
    )

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=100)
        parser.add_argument("--prefix", default="loadtest")
        parser.add_argument("--email-domain", default="example.com")
        parser.add_argument(
            "--role",
            choices=(Profile.Role.STUDENT, Profile.Role.TEACHER),
            default=Profile.Role.STUDENT,
        )
        parser.add_argument(
            "--password-env",
            default="ATLAS_LOAD_TEST_PASSWORD",
            help="Environment variable containing the shared test password.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate the requested account pool without writing to the database.",
        )

    def handle(self, *args, **options):
        count = options["count"]
        prefix = options["prefix"].strip().lower()
        domain = options["email_domain"].strip().lower()
        role = options["role"]
        password_env = options["password_env"]
        password = os.getenv(password_env, "")

        self._validate_options(count, prefix, domain, role, password, password_env)
        emails = [f"{prefix}{number:03d}@{domain}" for number in range(1, count + 1)]
        self._validate_lengths(emails)

        if options["dry_run"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Validated {count} {role} load-test accounts: "
                    f"{emails[0]} through {emails[-1]}."
                )
            )
            return

        created = 0
        updated = 0
        with transaction.atomic():
            for number, email in enumerate(emails, start=1):
                was_created = self._upsert_user(number, email, role, password)
                created += int(was_created)
                updated += int(not was_created)

        self.stdout.write(
            self.style.SUCCESS(
                f"Load-test account pool ready: {created} created, {updated} updated "
                f"({emails[0]} through {emails[-1]})."
            )
        )

    @staticmethod
    def _validate_options(count, prefix, domain, role, password, password_env):
        if not 1 <= count <= 1000:
            raise CommandError("--count must be between 1 and 1000.")
        if not prefix or any(character.isspace() for character in prefix):
            raise CommandError("--prefix must be non-empty and contain no whitespace.")
        if not domain or "." not in domain or any(
            character.isspace() for character in domain
        ):
            raise CommandError("--email-domain must be a valid domain name.")
        if role == Profile.Role.TEACHER and not domain.endswith("deped.gov.ph"):
            raise CommandError(
                "Teacher load-test accounts must use a deped.gov.ph email domain."
            )
        if not password:
            raise CommandError(
                f"Set the {password_env} environment variable before running this command."
            )
        if len(password) < 12:
            raise CommandError("The load-test password must contain at least 12 characters.")

    @staticmethod
    def _validate_lengths(emails):
        User = get_user_model()
        username_max = User._meta.get_field(User.USERNAME_FIELD).max_length
        email_max = User._meta.get_field("email").max_length
        if any(len(email) > username_max or len(email) > email_max for email in emails):
            raise CommandError("The generated email addresses exceed the user-model limits.")

    @staticmethod
    def _upsert_user(number, email, role, password):
        User = get_user_model()
        conflicting_user = User.objects.filter(email__iexact=email).exclude(
            **{User.USERNAME_FIELD: email}
        ).first()
        if conflicting_user:
            raise CommandError(
                f"Refusing to reuse {email}; it belongs to another account."
            )

        user, created = User.objects.get_or_create(
            **{User.USERNAME_FIELD: email},
            defaults={
                "email": email,
                "first_name": "Load Test",
                "last_name": f"User {number:03d}",
                "is_active": True,
                "is_staff": False,
                "is_superuser": False,
            },
        )
        if not created and (user.is_staff or user.is_superuser):
            raise CommandError(f"Refusing to modify privileged account {email}.")

        user.email = email
        user.first_name = "Load Test"
        user.last_name = f"User {number:03d}"
        user.is_active = True
        user.set_password(password)
        user.save()

        profile, _ = Profile.objects.get_or_create(user=user)
        profile.role = role
        consented_at = timezone.now()
        profile.privacy_consent_accepted_at = consented_at
        profile.privacy_consent_version = settings.PRIVACY_CONSENT_VERSION
        profile.age_consent_confirmed_at = consented_at
        profile.age_consent_version = settings.PRIVACY_CONSENT_VERSION
        profile.save()

        EmailAddress.objects.update_or_create(
            user=user,
            email=email,
            defaults={"verified": True, "primary": True},
        )
        return created
