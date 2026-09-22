from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from atlas.storage import R2StorageConfig


class R2StorageConfigTests(SimpleTestCase):
    environment = {
        "R2_ACCOUNT_ID": "a" * 32,
        "R2_ACCESS_KEY_ID": "test-access-key",
        "R2_SECRET_ACCESS_KEY": "test-secret-key",
        "R2_BUCKET_NAME": "atlas-test-files",
    }

    def test_builds_private_signed_storage_options(self):
        config = R2StorageConfig.from_environment(self.environment)

        options = config.storage_options()

        self.assertEqual(
            options["endpoint_url"],
            f"https://{'a' * 32}.r2.cloudflarestorage.com",
        )
        self.assertEqual(options["bucket_name"], "atlas-test-files")
        self.assertEqual(options["region_name"], "auto")
        self.assertIsNone(options["default_acl"])
        self.assertTrue(options["querystring_auth"])
        self.assertFalse(options["file_overwrite"])

    def test_rejects_endpoint_containing_bucket_path(self):
        environment = {
            **self.environment,
            "R2_ENDPOINT_URL": (
                f"https://{'a' * 32}.r2.cloudflarestorage.com/atlas-test-files"
            ),
        }

        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "account endpoint without a bucket path",
        ):
            R2StorageConfig.from_environment(environment)

    def test_reports_missing_credentials_without_echoing_values(self):
        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "R2_SECRET_ACCESS_KEY",
        ):
            R2StorageConfig.from_environment(
                {**self.environment, "R2_SECRET_ACCESS_KEY": ""}
            )

    def test_rejects_excessive_signed_url_lifetime(self):
        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "between 1 and 604800",
        ):
            R2StorageConfig.from_environment(
                {**self.environment, "R2_SIGNED_URL_EXPIRY": "604801"}
            )
