"""Deployment health and production-audit regression coverage."""

from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from django.urls import reverse

from library.services.deployment import DeploymentReadinessService
from library.views.public import HealthCheckView


class HealthCheckTests(SimpleTestCase):
    databases = {"default"}

    def test_health_endpoint_reports_database_ready_without_sensitive_details(self):
        response = self.client.get(reverse("library:health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "ok", "checks": {"database": "ok"}},
        )
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertNotContains(response, "password", status_code=200)

    @patch.object(HealthCheckView, "service_class")
    def test_health_endpoint_returns_503_when_database_is_unavailable(self, service):
        service.return_value.check.return_value = (
            {
                "status": "unavailable",
                "checks": {"database": "unavailable"},
            },
            False,
        )

        response = self.client.get(reverse("library:health"))

        self.assertEqual(response.status_code, 503)


class DeploymentReadinessServiceTests(SimpleTestCase):
    @override_settings(
        ACCOUNT_EMAIL_VERIFICATION="mandatory",
        EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend",
        AI_DETECTION_PRIMARY_REVISION="main",
        AI_DETECTION_ENABLE_VALIDATION=True,
        AI_DETECTION_VALIDATION_REVISION="main",
        ADMIN_URL_PATH="admin",
        BUSINESS_ADDRESS="",
        RATE_LIMIT_ENABLED=False,
        STORAGES={
            "default": {
                "BACKEND": "django.core.files.storage.FileSystemStorage"
            },
            "staticfiles": {
                "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
            },
        },
    )
    @patch.dict("os.environ", {"HF_HOME": ""})
    def test_unsafe_production_configuration_has_actionable_findings(self):
        findings = DeploymentReadinessService().inspect_configuration()
        codes = {finding.code for finding in findings}

        self.assertTrue(
            {"atlas.E002", "atlas.E003", "atlas.E004", "atlas.E005"}
            <= codes
        )
        self.assertTrue(
            {"atlas.W001", "atlas.W002", "atlas.W003", "atlas.W004"}
            <= codes
        )

    @override_settings(
        ACCOUNT_EMAIL_VERIFICATION="mandatory",
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        EMAIL_HOST_USER="atlas@example.edu",
        EMAIL_HOST_PASSWORD="test-production-secret",
        AI_DETECTION_PRIMARY_REVISION="a1b2c3d4",
        AI_DETECTION_ENABLE_VALIDATION=False,
        ADMIN_URL_PATH="private-atlas-console",
        BUSINESS_ADDRESS="Manila, Philippines",
        RATE_LIMIT_ENABLED=True,
        STORAGES={
            "default": {"BACKEND": "tests.storage.PrivateStorage"},
            "staticfiles": {
                "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
            },
        },
    )
    @patch.dict("os.environ", {"HF_HOME": "/persistent/huggingface"})
    def test_safe_configuration_has_no_atlas_findings(self):
        findings = DeploymentReadinessService().inspect_configuration()

        self.assertEqual(findings, [])
