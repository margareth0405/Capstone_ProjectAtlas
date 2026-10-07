"""Verify that the development configuration can run without cloud services."""

from pathlib import Path
from typing import ClassVar

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = "Verify local PostgreSQL, filesystem media, email, and AI configuration."

    local_database_hosts: ClassVar[frozenset[str]] = frozenset(
        {"", "localhost", "127.0.0.1", "::1"}
    )
    offline_email_backends: ClassVar[frozenset[str]] = frozenset(
        {
            "django.core.mail.backends.console.EmailBackend",
            "django.core.mail.backends.filebased.EmailBackend",
            "django.core.mail.backends.locmem.EmailBackend",
            "django.core.mail.backends.dummy.EmailBackend",
        }
    )
    required_onnx_files: ClassVar[frozenset[str]] = frozenset(
        {
            "model_int8.onnx",
            "tokenizer.json",
            "tokenizer_config.json",
            "label_order.json",
        }
    )

    def handle(self, *args, **options):
        problems = self._configuration_problems()
        if problems:
            details = "\n".join(f"- {problem}" for problem in problems)
            raise CommandError(
                "ATLAS is not configured for offline local use:\n"
                f"{details}\n"
                "Use local values in .env; keep the cloud values in Render."
            )

        self._check_database()
        self._check_storage()
        self.stdout.write(
            self.style.SUCCESS(
                "Offline local configuration passed: PostgreSQL and media are local; "
                "email and AI do not require a cloud service."
            )
        )

    def _configuration_problems(self):
        problems = []
        database = settings.DATABASES["default"]
        database_host = str(database.get("HOST", "")).strip().lower()
        if database.get("ENGINE") != "django.db.backends.postgresql":
            problems.append("DATABASE_URL must use PostgreSQL.")
        if database_host not in self.local_database_hosts:
            problems.append(
                "DATABASE_URL points to a remote host. Use localhost for offline work."
            )

        storage_backend = settings.STORAGES["default"].get("BACKEND", "")
        if storage_backend != "django.core.files.storage.FileSystemStorage":
            problems.append(
                "R2_STORAGE_ENABLED must be False so media uses the local media folder."
            )

        if settings.EMAIL_BACKEND not in self.offline_email_backends:
            problems.append(
                "EMAIL_BACKEND must be console, file, memory, or dummy instead of SMTP/API."
            )

        ai_engine = settings.AI_DETECTION_ENGINE.strip().lower()
        if ai_engine == "remote":
            problems.append("AI_DETECTION_ENGINE cannot be remote for offline work.")
        elif ai_engine == "onnx":
            model_directory = Path(settings.AI_DETECTION_MODEL_DIR)
            missing = sorted(
                filename
                for filename in self.required_onnx_files
                if not (model_directory / filename).is_file()
            )
            if missing:
                problems.append(
                    "The local ONNX model is incomplete; missing: " + ", ".join(missing)
                )

        return problems

    def _check_database(self):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                if cursor.fetchone() != (1,):
                    raise CommandError(
                        "Local PostgreSQL returned an unexpected result."
                    )
        except CommandError:
            raise
        except Exception as exc:
            raise CommandError(
                "Local PostgreSQL is unavailable. Start the Windows PostgreSQL service "
                "and check DATABASE_URL."
            ) from exc

    def _check_storage(self):
        probe_name = "_atlas_storage_checks/offline-local-probe.txt"
        saved_name = ""
        try:
            saved_name = default_storage.save(
                probe_name,
                ContentFile(b"ATLAS offline local storage check"),
            )
            with default_storage.open(saved_name, "rb") as probe:
                if probe.read() != b"ATLAS offline local storage check":
                    raise CommandError(
                        "Local media storage returned unexpected content."
                    )
        except CommandError:
            raise
        except Exception as exc:
            raise CommandError(
                "The local media folder is not writable. Check MEDIA_ROOT permissions."
            ) from exc
        finally:
            if saved_name:
                default_storage.delete(saved_name)
