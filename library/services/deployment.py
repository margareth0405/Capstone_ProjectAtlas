"""Operational health and production-configuration services."""

from __future__ import annotations

import os
from dataclasses import dataclass
from email.utils import parseaddr

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import connections
from django.db.migrations.executor import MigrationExecutor
from django.db.utils import DatabaseError


@dataclass(frozen=True)
class DeploymentFinding:
    """One actionable production-readiness result."""

    code: str
    message: str
    hint: str
    severity: str = "warning"


class HealthCheckService:
    """Run dependency checks without exposing credentials or database details."""

    database_alias = "default"

    def check(self):
        try:
            connection = connections[self.database_alias]
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                database_ok = cursor.fetchone() == (1,)
        except (DatabaseError, OSError):
            database_ok = False

        healthy = database_ok
        return {
            "status": "ok" if healthy else "unavailable",
            "checks": {"database": "ok" if database_ok else "unavailable"},
        }, healthy


class DeploymentReadinessService:
    """Audit ATLAS-specific settings that Django's checks cannot infer."""

    development_email_backends = frozenset(
        {
            "django.core.mail.backends.console.EmailBackend",
            "django.core.mail.backends.dummy.EmailBackend",
            "django.core.mail.backends.locmem.EmailBackend",
        }
    )
    floating_revisions = frozenset({"", "main", "master", "latest"})
    placeholder_values = frozenset(
        {
            "replace-me",
            "replace-with-a-private-admin-path",
            "replace-with-the-institution-address",
        }
    )

    @classmethod
    def _is_missing_or_placeholder(cls, value):
        normalized = str(value).strip().lower()
        return not normalized or normalized in cls.placeholder_values or normalized.startswith(
            "replace-"
        )

    @staticmethod
    def _is_valid_email(value):
        _display_name, address = parseaddr(str(value))
        try:
            validate_email(address)
        except ValidationError:
            return False
        return True

    def inspect_configuration(self):
        findings = []
        database_engine = settings.DATABASES["default"].get("ENGINE", "")
        if database_engine != "django.db.backends.postgresql":
            findings.append(
                DeploymentFinding(
                    code="atlas.E001",
                    severity="error",
                    message="ATLAS is not configured to use PostgreSQL.",
                    hint="Set DATABASE_URL to a PostgreSQL connection URL.",
                )
            )

        if settings.EMAIL_BACKEND in self.development_email_backends:
            findings.append(
                DeploymentFinding(
                    code="atlas.E002",
                    severity="error",
                    message=(
                        "Account and contact email is using a non-delivery backend."
                    ),
                    hint=(
                        "Configure the SMTP email backend and test delivery before "
                        "launch."
                    ),
                )
            )

        smtp_enabled = (
            settings.EMAIL_BACKEND
            == "django.core.mail.backends.smtp.EmailBackend"
        )
        if smtp_enabled and (
            self._is_missing_or_placeholder(settings.EMAIL_HOST_USER)
            or self._is_missing_or_placeholder(settings.EMAIL_HOST_PASSWORD)
        ):
            findings.append(
                DeploymentFinding(
                    code="atlas.E006",
                    severity="error",
                    message="ATLAS email delivery has incomplete SMTP credentials.",
                    hint="Set EMAIL_HOST_USER and EMAIL_HOST_PASSWORD to working secrets.",
                )
            )

        if smtp_enabled and not settings.EMAIL_HOST.strip():
            findings.append(
                DeploymentFinding(
                    code="atlas.E007",
                    severity="error",
                    message="ATLAS email delivery has no SMTP host.",
                    hint="Set EMAIL_HOST to the SMTP server hostname.",
                )
            )

        if not self._is_valid_email(settings.DEFAULT_FROM_EMAIL):
            findings.append(
                DeploymentFinding(
                    code="atlas.E008",
                    severity="error",
                    message="DEFAULT_FROM_EMAIL is not a valid mailbox.",
                    hint="Use a value such as ATLAS <repository@example.edu>.",
                )
            )

        if not self._is_valid_email(settings.SUPPORT_EMAIL):
            findings.append(
                DeploymentFinding(
                    code="atlas.E009",
                    severity="error",
                    message="SUPPORT_EMAIL is not a valid mailbox.",
                    hint="Set SUPPORT_EMAIL to the inbox that receives contact requests.",
                )
            )

        if not settings.DEBUG and settings.ACCOUNT_DEFAULT_HTTP_PROTOCOL != "https":
            findings.append(
                DeploymentFinding(
                    code="atlas.E010",
                    severity="error",
                    message="Production account email links are not configured for HTTPS.",
                    hint="Set ACCOUNT_DEFAULT_HTTP_PROTOCOL=https on Render.",
                )
            )

        if not settings.DEBUG and settings.SITE_ID != 1:
            findings.append(
                DeploymentFinding(
                    code="atlas.E011",
                    severity="error",
                    message="Production is not using the ATLAS Site record.",
                    hint="Set SITE_ID=1 on Render.",
                )
            )

        ai_engine = settings.AI_DETECTION_ENGINE.strip().lower()
        if ai_engine not in {"fast", "transformer"}:
            findings.append(
                DeploymentFinding(
                    code="atlas.E012",
                    severity="error",
                    message="The AI Detection engine is not supported.",
                    hint="Set AI_DETECTION_ENGINE to fast or transformer.",
                )
            )

        primary_revision = settings.AI_DETECTION_PRIMARY_REVISION.strip().lower()
        if ai_engine == "transformer" and primary_revision in self.floating_revisions:
            findings.append(
                DeploymentFinding(
                    code="atlas.E003",
                    severity="error",
                    message="The primary AI detector uses a floating model revision.",
                    hint=(
                        "Set AI_DETECTION_PRIMARY_REVISION to a Hugging Face commit "
                        "hash for reproducible results."
                    ),
                )
            )

        validation_revision = settings.AI_DETECTION_VALIDATION_REVISION.strip().lower()
        if (
            settings.AI_DETECTION_ENABLE_VALIDATION
            and validation_revision in self.floating_revisions
        ):
            findings.append(
                DeploymentFinding(
                    code="atlas.E004",
                    severity="error",
                    message="The optional AI validator uses a floating model revision.",
                    hint=(
                        "Pin AI_DETECTION_VALIDATION_REVISION before enabling the "
                        "validator in production."
                    ),
                )
            )

        admin_path = settings.ADMIN_URL_PATH.strip().lower()
        if admin_path in {"admin", *self.placeholder_values}:
            findings.append(
                DeploymentFinding(
                    code="atlas.E005",
                    severity="error",
                    message="The administrator URL is still common or a placeholder.",
                    hint="Set DJANGO_ADMIN_PATH to a private, unguessable path.",
                )
            )

        business_address = settings.BUSINESS_ADDRESS.strip().lower()
        if self._is_missing_or_placeholder(business_address):
            findings.append(
                DeploymentFinding(
                    code="atlas.W001",
                    message="The institution's public business address is missing.",
                    hint=(
                        "Set BUSINESS_ADDRESS to the responsible institution's exact "
                        "address before public launch."
                    ),
                )
            )

        storage_backend = settings.STORAGES["default"].get("BACKEND", "")
        if storage_backend == "django.core.files.storage.FileSystemStorage":
            findings.append(
                DeploymentFinding(
                    code="atlas.W002",
                    message="Uploaded media uses local filesystem storage.",
                    hint=(
                        "Mount durable private storage and back it up, or configure a "
                        "private remote storage backend."
                    ),
                )
            )

        if (
            ai_engine == "transformer" or settings.AI_DETECTION_ENABLE_VALIDATION
        ) and not os.getenv("HF_HOME", "").strip():
            findings.append(
                DeploymentFinding(
                    code="atlas.W003",
                    message="HF_HOME is not explicitly configured.",
                    hint=(
                        "Point HF_HOME at persistent storage so deployments do not "
                        "re-download the AI model."
                    ),
                )
            )

        if not settings.RATE_LIMIT_ENABLED:
            findings.append(
                DeploymentFinding(
                    code="atlas.W004",
                    message="Application rate limiting is disabled.",
                    hint="Set RATE_LIMIT_ENABLED=True for a public deployment.",
                )
            )
        return findings

    def pending_migrations(self):
        """Return unapplied migration identifiers for the configured database."""

        connection = connections["default"]
        executor = MigrationExecutor(connection)
        targets = executor.loader.graph.leaf_nodes()
        return [
            f"{migration.app_label}.{migration.name}"
            for migration, _backwards in executor.migration_plan(targets)
        ]
