"""ASGI config for ATLAS."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "atlas.settings")
application = get_asgi_application()
