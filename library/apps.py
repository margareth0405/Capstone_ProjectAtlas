from django.apps import AppConfig


class LibraryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "library"
    verbose_name = "Atlas Library"

    def ready(self):
        # Import registers ATLAS-specific checks with Django's check framework.
        from . import checks  # noqa: F401

