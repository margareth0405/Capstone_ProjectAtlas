"""Django application metadata for AI Detection routes."""

from django.apps import AppConfig


class AIDetectionConfig(AppConfig):
    """Identify the focused AI Detection routing application to Django."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "ai_detection"
    verbose_name = "ATLAS AI Detection"
