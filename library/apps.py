"""Library application startup hooks and configured-site initialization."""

from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate


def ensure_configured_site(sender, **kwargs):
    """Ensure django-allauth can resolve the configured site after deployment."""

    from django.contrib.sites.models import Site

    Site.objects.get_or_create(
        id=settings.SITE_ID,
        defaults={
            "domain": settings.SITE_DOMAIN,
            "name": settings.SITE_DISPLAY_NAME,
        },
    )


class LibraryConfig(AppConfig):
    """Register ATLAS checks and post-migration site initialization."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "library"
    verbose_name = "ATLAS"

    def ready(self):
        # Import registers ATLAS-specific checks with Django's check framework.
        from . import checks  # noqa: F401

        post_migrate.connect(
            ensure_configured_site,
            sender=self,
            dispatch_uid="library.ensure_configured_site",
        )

