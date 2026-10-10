"""Provision opt-in demonstration accounts during a hosted deployment."""

import os
from dataclasses import dataclass

from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from library.models import Profile
from library.services.accounts import AccountEmailPolicy

TRUTHY_VALUES = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class DemoAccount:
    """Environment-backed identity and authorization settings for one account."""

    label: str
    username: str
    email: str
    full_name: str
    password: str
    password_env: str
    role: str | None = None
    is_staff: bool = False
    is_superuser: bool = False


class Command(BaseCommand):
    """Create the four hosted demonstration identities without requiring a shell."""

    help = (
        "Idempotently provision verified Student, Teacher, Administrator, and "
        "Superuser demonstration accounts from private environment variables."
    )

    def handle(self, *args, **options):
        del args, options
        if os.getenv("ATLAS_PROVISION_DEMO_ACCOUNTS", "").strip().lower() not in (
            TRUTHY_VALUES
        ):
            self.stdout.write(
                "Demo account provisioning is disabled; no accounts were changed."
            )
            return

        accounts = self._accounts_from_environment()
        self._validate_accounts(accounts)

        created = 0
        updated = 0
        with transaction.atomic():
            for account in accounts:
                was_created = self._upsert_account(account)
                created += int(was_created)
                updated += int(not was_created)

        self.stdout.write(
            self.style.SUCCESS(
                "Demo accounts ready: "
                f"{created} created, {updated} updated. Passwords were not logged."
            )
        )

    @staticmethod
    def _value(name, default=""):
        return os.getenv(name, default).strip()

    def _accounts_from_environment(self):
        return (
            DemoAccount(
                label="Student",
                username=self._value(
                    "ATLAS_DEMO_STUDENT_EMAIL", "student@atlas.edu"
                ).lower(),
                email=self._value(
                    "ATLAS_DEMO_STUDENT_EMAIL", "student@atlas.edu"
                ).lower(),
                full_name=self._value("ATLAS_DEMO_STUDENT_NAME", "Demo Student"),
                password=os.getenv("ATLAS_DEMO_STUDENT_PASSWORD", ""),
                password_env="ATLAS_DEMO_STUDENT_PASSWORD",
                role=Profile.Role.STUDENT,
            ),
            DemoAccount(
                label="Teacher",
                username=self._value(
                    "ATLAS_DEMO_TEACHER_EMAIL", "teacher@deped.gov.ph"
                ).lower(),
                email=self._value(
                    "ATLAS_DEMO_TEACHER_EMAIL", "teacher@deped.gov.ph"
                ).lower(),
                full_name=self._value("ATLAS_DEMO_TEACHER_NAME", "Demo Teacher"),
                password=os.getenv("ATLAS_DEMO_TEACHER_PASSWORD", ""),
                password_env="ATLAS_DEMO_TEACHER_PASSWORD",
                role=Profile.Role.TEACHER,
            ),
            DemoAccount(
                label="Administrator",
                username=self._value("ATLAS_DEMO_ADMIN_USERNAME", "atlas_demo_admin"),
                email=self._value(
                    "ATLAS_DEMO_ADMIN_EMAIL", "demo.administrator@example.com"
                ).lower(),
                full_name=self._value("ATLAS_DEMO_ADMIN_NAME", "Demo Administrator"),
                password=os.getenv("ATLAS_DEMO_ADMIN_PASSWORD", ""),
                password_env="ATLAS_DEMO_ADMIN_PASSWORD",
                is_staff=True,
            ),
            DemoAccount(
                label="Superuser",
                username=self._value(
                    "ATLAS_DEMO_SUPERUSER_USERNAME", "atlas_demo_superuser"
                ),
                email=self._value(
                    "ATLAS_DEMO_SUPERUSER_EMAIL", "demo.superuser@example.com"
                ).lower(),
                full_name=self._value("ATLAS_DEMO_SUPERUSER_NAME", "Demo Superuser"),
                password=os.getenv("ATLAS_DEMO_SUPERUSER_PASSWORD", ""),
                password_env="ATLAS_DEMO_SUPERUSER_PASSWORD",
                is_staff=True,
                is_superuser=True,
            ),
        )

    def _validate_accounts(self, accounts):
        usernames = set()
        emails = set()
        for account in accounts:
            if not account.password:
                raise CommandError(
                    f"Set {account.password_env} before enabling demo accounts."
                )
            if not account.username:
                raise CommandError(f"The {account.label} username cannot be empty.")
            if not account.full_name:
                raise CommandError(f"The {account.label} name cannot be empty.")
            try:
                validate_email(account.email)
            except ValidationError as exc:
                raise CommandError(
                    f"The {account.label} email address is invalid."
                ) from exc

            normalized_username = account.username.casefold()
            normalized_email = account.email.casefold()
            if normalized_username in usernames:
                raise CommandError("Demo account usernames must be unique.")
            if normalized_email in emails:
                raise CommandError("Demo account email addresses must be unique.")
            usernames.add(normalized_username)
            emails.add(normalized_email)

            if account.role:
                policy_error = AccountEmailPolicy().error_for(
                    email=account.email,
                    role=account.role,
                )
                if policy_error:
                    raise CommandError(f"{account.label}: {policy_error}")

            candidate = get_user_model()(
                username=account.username,
                email=account.email,
                first_name=self._split_name(account.full_name)[0],
                last_name=self._split_name(account.full_name)[1],
            )
            try:
                password_validation.validate_password(account.password, candidate)
            except ValidationError as exc:
                raise CommandError(
                    f"{account.password_env} is not acceptable: {' '.join(exc.messages)}"
                ) from exc

    @staticmethod
    def _split_name(full_name):
        normalized = " ".join(full_name.split())
        return normalized.partition(" ")[::2]

    def _upsert_account(self, account):
        User = get_user_model()
        matches = list(
            User.objects.select_for_update().filter(
                Q(username__iexact=account.username) | Q(email__iexact=account.email)
            )
        )
        distinct_ids = {user.pk for user in matches}
        if len(distinct_ids) > 1:
            raise CommandError(
                f"Refusing to merge conflicting {account.label} username/email records."
            )

        email_owner = (
            EmailAddress.objects.filter(email__iexact=account.email)
            .exclude(user_id=next(iter(distinct_ids), None))
            .first()
        )
        if email_owner:
            raise CommandError(
                f"Refusing to reuse the {account.label} email; it belongs to another account."
            )

        created = not matches
        user = matches[0] if matches else User()
        first_name, last_name = self._split_name(account.full_name)
        user.username = account.username
        user.email = account.email
        user.first_name = first_name
        user.last_name = last_name
        user.is_active = True
        user.is_staff = account.is_staff
        user.is_superuser = account.is_superuser
        user.set_password(account.password)
        try:
            user.full_clean(exclude=("password",))
        except ValidationError as exc:
            raise CommandError(
                f"The {account.label} account details are invalid: {exc}"
            ) from exc
        user.save()

        if account.role:
            consented_at = timezone.now()
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.role = account.role
            profile.privacy_consent_accepted_at = consented_at
            profile.privacy_consent_version = settings.PRIVACY_CONSENT_VERSION
            profile.age_consent_confirmed_at = consented_at
            profile.age_consent_version = settings.PRIVACY_CONSENT_VERSION
            profile.save()

        EmailAddress.objects.filter(user=user).exclude(
            email__iexact=account.email
        ).update(primary=False)
        email_identity = EmailAddress.objects.filter(
            user=user,
            email__iexact=account.email,
        ).first()
        if email_identity is None:
            email_identity = EmailAddress(user=user, email=account.email)
        email_identity.email = account.email
        email_identity.verified = True
        email_identity.primary = True
        email_identity.save()
        return created
