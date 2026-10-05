"""Django application metadata for Digital Sources repository routes."""

from django.apps import AppConfig


class RepositoryConfig(AppConfig):
    """Identify the focused repository-routing application to Django."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "repository"
    verbose_name = "Digital Sources"
