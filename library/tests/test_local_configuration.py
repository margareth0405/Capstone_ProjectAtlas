from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import ClassVar
from unittest.mock import patch

from django.core.management import CommandError, call_command
from django.test import SimpleTestCase, override_settings


class LocalConfigurationCommandTests(SimpleTestCase):
    local_database: ClassVar[dict[str, dict[str, str]]] = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "HOST": "localhost",
        }
    }
    local_storage: ClassVar[dict[str, dict[str, object]]] = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    }

    @override_settings(
        DATABASES=local_database,
        STORAGES=local_storage,
        EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend",
        AI_DETECTION_ENGINE="fast",
    )
    @patch("library.management.commands.check_local.Command._check_storage")
    @patch("library.management.commands.check_local.Command._check_database")
    def test_accepts_offline_local_configuration(self, database_check, storage_check):
        output = StringIO()

        call_command("check_local", stdout=output)

        database_check.assert_called_once_with()
        storage_check.assert_called_once_with()
        self.assertIn("Offline local configuration passed", output.getvalue())

    @override_settings(
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "HOST": "cloud.example.test",
            }
        },
        STORAGES={
            "default": {"BACKEND": "storages.backends.s3.S3Storage"},
            "staticfiles": {
                "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
            },
        },
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        AI_DETECTION_ENGINE="remote",
    )
    def test_rejects_cloud_dependencies(self):
        with self.assertRaisesMessage(CommandError, "not configured for offline"):
            call_command("check_local")

    @override_settings(
        DATABASES=local_database,
        STORAGES=local_storage,
        EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend",
        AI_DETECTION_ENGINE="onnx",
    )
    def test_reports_missing_local_onnx_files(self):
        with (
            TemporaryDirectory() as model_directory,
            override_settings(AI_DETECTION_MODEL_DIR=Path(model_directory)),
            self.assertRaisesMessage(CommandError, "model_int8.onnx"),
        ):
            call_command("check_local")
