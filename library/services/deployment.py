"""Operational health and production-configuration services."""

from __future__ import annotations

import os
from dataclasses import dataclass
from email.utils import parseaddr
from pathlib import Path
from urllib.parse import urlsplit

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
        return (
            not normalized
            or normalized in cls.placeholder_values
            or normalized.startswith("replace-")
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
            settings.EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend"
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
        if ai_engine not in {"onnx", "fast", "transformer", "remote"}:
            findings.append(
                DeploymentFinding(
                    code="atlas.E012",
                    severity="error",
                    message="The AI Detection engine is not supported.",
                    hint=(
                        "Set AI_DETECTION_ENGINE to onnx, fast, transformer, or remote."
                    ),
                )
            )

        primary_revision = settings.AI_DETECTION_PRIMARY_REVISION.strip().lower()
        if (
            ai_engine in {"onnx", "transformer", "remote"}
            and primary_revision in self.floating_revisions
        ):
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

        if ai_engine == "onnx":
            required_model_files = (
                "model_int8.onnx",
                "tokenizer.json",
                "tokenizer_config.json",
                "label_order.json",
            )
            missing_model_files = [
                filename
                for filename in required_model_files
                if not (Path(settings.AI_DETECTION_MODEL_DIR) / filename).is_file()
            ]
            if missing_model_files:
                findings.append(
                    DeploymentFinding(
                        code="atlas.E016",
                        severity="error",
                        message="The pinned local ONNX detector files are missing.",
                        hint=(
                            "Run 'python manage.py download_ai_model' on the "
                            "development computer and include models/ai_detector "
                            "in the deployment."
                        ),
                    )
                )

        if ai_engine == "remote":
            remote_url = settings.AI_DETECTION_REMOTE_URL
            parsed_remote_url = urlsplit(remote_url)
            if (
                parsed_remote_url.scheme not in {"http", "https"}
                or not parsed_remote_url.netloc
                or parsed_remote_url.username
                or parsed_remote_url.password
                or parsed_remote_url.query
                or parsed_remote_url.fragment
            ):
                findings.append(
                    DeploymentFinding(
                        code="atlas.E014",
                        severity="error",
                        message="The dedicated AI inference URL is missing or invalid.",
                        hint=(
                            "Set AI_DETECTION_REMOTE_URL to the private Render "
                            "service URL without credentials or query parameters."
                        ),
                    )
                )
            if len(settings.AI_DETECTION_REMOTE_TOKEN) < 32:
                findings.append(
                    DeploymentFinding(
                        code="atlas.E015",
                        severity="error",
                        message="The dedicated AI inference token is missing or too short.",
                        hint=(
                            "Set matching random AI_DETECTION_REMOTE_TOKEN and "
                            "AI_INFERENCE_TOKEN values of at least 32 characters."
                        ),
                    )
                )

        comparison_revision = settings.AI_DETECTION_COMPARISON_REVISION.strip().lower()
        if (
            ai_engine == "transformer"
            and comparison_revision in self.floating_revisions
        ):
            findings.append(
                DeploymentFinding(
                    code="atlas.E004",
                    severity="error",
                    message="The Vanguard benchmark uses a floating model revision.",
                    hint=(
                        "Set AI_DETECTION_COMPARISON_REVISION to a Hugging Face "
                        "commit hash for reproducible benchmarks."
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
            production = not settings.DEBUG
            findings.append(
                DeploymentFinding(
                    code="atlas.E013" if production else "atlas.W002",
                    severity="error" if production else "warning",
                    message=(
                        "Production uploads use ephemeral local filesystem storage."
                        if production
                        else "Uploaded media uses local filesystem storage."
                    ),
                    hint=(
                        "Configure private Cloudflare R2 storage before deploying. "
                        "Local media files are removed when an ephemeral host restarts."
                        if production
                        else "Use private Cloudflare R2 storage before deploying to an "
                        "ephemeral host."
                    ),
                )
            )

        if ai_engine == "transformer" and not os.getenv("HF_HOME", "").strip():
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

        if "*" in settings.ALLOWED_HOSTS:
            findings.append(
                DeploymentFinding(
                    code="atlas.E017",
                    severity="error",
                    message="ALLOWED_HOSTS trusts every Host header.",
                    hint=(
                        "Set DJANGO_ALLOWED_HOSTS to the exact production hostname(s); "
                        "do not use '*'."
                    ),
                )
            )

        if not settings.DEBUG:
            insecure_origins = [
                origin
                for origin in settings.CSRF_TRUSTED_ORIGINS
                if not origin.startswith("https://")
            ]
            if insecure_origins:
                findings.append(
                    DeploymentFinding(
                        code="atlas.E018",
                        severity="error",
                        message="A production CSRF trusted origin does not use HTTPS.",
                        hint=(
                            "Use only https:// origins in DJANGO_CSRF_TRUSTED_ORIGINS."
                        ),
                    )
                )

        if not settings.RATE_LIMIT_ENABLED:
            findings.append(
                DeploymentFinding(
                    code="atlas.E019",
                    severity="error",
                    message="Application rate limiting is disabled.",
                    hint="Set RATE_LIMIT_ENABLED=True for a public deployment.",
                )
            )
        else:
            rate_settings = (
                "RATE_LIMIT_SEARCH_REQUESTS",
                "RATE_LIMIT_SEARCH_WINDOW",
                "RATE_LIMIT_LOGIN_REQUESTS",
                "RATE_LIMIT_LOGIN_WINDOW",
                "RATE_LIMIT_REGISTER_REQUESTS",
                "RATE_LIMIT_REGISTER_WINDOW",
                "RATE_LIMIT_CONTACT_REQUESTS",
                "RATE_LIMIT_CONTACT_WINDOW",
                "RATE_LIMIT_EMAIL_REQUESTS",
                "RATE_LIMIT_EMAIL_WINDOW",
                "RATE_LIMIT_UPLOAD_REQUESTS",
                "RATE_LIMIT_UPLOAD_WINDOW",
                "RATE_LIMIT_AI_REQUESTS",
                "RATE_LIMIT_AI_WINDOW",
                "RATE_LIMIT_STAFF_REQUESTS",
                "RATE_LIMIT_STAFF_WINDOW",
            )
            invalid_rate_settings = [
                name for name in rate_settings if getattr(settings, name) <= 0
            ]
            if invalid_rate_settings:
                findings.append(
                    DeploymentFinding(
                        code="atlas.E020",
                        severity="error",
                        message="One or more rate-limit values disable protection.",
                        hint=(
                            "Set every rate-limit request and window value to a "
                            "positive integer: " + ", ".join(invalid_rate_settings)
                        ),
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
