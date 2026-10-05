"""Django application metadata for ATLAS account routes."""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Identify the focused account-routing application to Django."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    verbose_name = "ATLAS Accounts"
