"""Validated configuration for ATLAS private Cloudflare R2 storage."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured


@dataclass(frozen=True)
class R2StorageConfig:
    """Build django-storages options without exposing secrets in settings files."""

    account_id: str
    access_key_id: str
    secret_access_key: str
    bucket_name: str
    endpoint_url: str
    signed_url_expiry: int = 300

    @classmethod
    def from_environment(cls, environ: Mapping[str, str]):
        required_names = (
            "R2_ACCOUNT_ID",
            "R2_ACCESS_KEY_ID",
            "R2_SECRET_ACCESS_KEY",
            "R2_BUCKET_NAME",
        )
        values = {name: environ.get(name, "").strip() for name in required_names}
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise ImproperlyConfigured(
                "R2 storage is enabled but these settings are missing: "
                + ", ".join(missing)
            )

        account_id = values["R2_ACCOUNT_ID"].lower()
        if not re.fullmatch(r"[0-9a-f]{32}", account_id):
            raise ImproperlyConfigured("R2_ACCOUNT_ID must be a 32-character ID.")

        endpoint_url = environ.get("R2_ENDPOINT_URL", "").strip()
        if not endpoint_url:
            endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"
        endpoint_url = endpoint_url.rstrip("/")
        cls._validate_endpoint(endpoint_url, account_id)

        try:
            signed_url_expiry = int(environ.get("R2_SIGNED_URL_EXPIRY", "300"))
        except ValueError as exc:
            raise ImproperlyConfigured(
                "R2_SIGNED_URL_EXPIRY must be a whole number of seconds."
            ) from exc
        if not 1 <= signed_url_expiry <= 604800:
            raise ImproperlyConfigured(
                "R2_SIGNED_URL_EXPIRY must be between 1 and 604800 seconds."
            )

        return cls(
            account_id=account_id,
            access_key_id=values["R2_ACCESS_KEY_ID"],
            secret_access_key=values["R2_SECRET_ACCESS_KEY"],
            bucket_name=values["R2_BUCKET_NAME"],
            endpoint_url=endpoint_url,
            signed_url_expiry=signed_url_expiry,
        )

    @staticmethod
    def _validate_endpoint(endpoint_url: str, account_id: str):
        parsed = urlsplit(endpoint_url)
        hostname = (parsed.hostname or "").lower()
        if (
            parsed.scheme != "https"
            or parsed.username
            or parsed.password
            or parsed.port
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
            or not hostname.endswith(".r2.cloudflarestorage.com")
            or hostname.split(".", 1)[0] != account_id
        ):
            raise ImproperlyConfigured(
                "R2_ENDPOINT_URL must be the account endpoint without a bucket "
                "path, for example https://<ACCOUNT_ID>.r2.cloudflarestorage.com."
            )

    def storage_options(self):
        """Return private S3-compatible options accepted by django-storages."""
        return {
            "bucket_name": self.bucket_name,
            "access_key": self.access_key_id,
            "secret_key": self.secret_access_key,
            "endpoint_url": self.endpoint_url,
            "region_name": "auto",
            "signature_version": "s3v4",
            "addressing_style": "path",
            "default_acl": None,
            "querystring_auth": True,
            "querystring_expire": self.signed_url_expiry,
            "file_overwrite": False,
        }
