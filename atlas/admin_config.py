"""Django admin application configuration for the ATLAS admin site."""

from django.contrib.admin.apps import AdminConfig


class AtlasAdminConfig(AdminConfig):
    """Make Django discover and use the ATLAS-specific administration site."""

    default_site = "atlas.admin.AtlasAdminSite"
