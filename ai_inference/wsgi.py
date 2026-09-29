"""Render entry point for the private, high-memory Desklib service."""

import os

# The detector currently lives in the Django project. These settings satisfy
# Django initialization without granting this private service database access.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "atlas.settings")
os.environ.setdefault("SECRET_KEY", "inference-service-settings-only")
os.environ.setdefault("DATABASE_URL", "postgresql://unused:unused@127.0.0.1:9/unused")
os.environ.setdefault("DB_SSL_REQUIRE", "False")
os.environ.setdefault("DJANGO_ADMIN_PATH", "inference-service-disabled")
os.environ.setdefault("R2_STORAGE_ENABLED", "False")

import django

django.setup()

from django.conf import settings

from library.services.ai_detection import DesklibAcademicDetector

from .app import InferenceApplication, ModelState

detector = DesklibAcademicDetector(
    model_name=settings.AI_DETECTION_PRIMARY_MODEL,
    revision=settings.AI_DETECTION_PRIMARY_REVISION,
    allow_download=True,
)
model_state = ModelState(detector)
application = InferenceApplication(
    model_state,
    os.getenv("AI_INFERENCE_TOKEN", "").strip(),
)
