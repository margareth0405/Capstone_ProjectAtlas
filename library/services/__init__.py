"""Application service objects shared by ATLAS views and middleware."""

from .activity import ActivityRecorder
from .accounts import AccountEmailPolicy
from .ai_detection import (
    AIDetectionError,
    AIDetectionService,
    DesklibAcademicDetector,
    VanguardDetector,
)
from .catalog import CatalogQueryService
from .contact import ContactDeliveryError, ContactEmailService
from .context import GreetingNameResolver, PageContextBuilder, SupportContactPresenter
from .documents import DocumentExtractionError, DocumentTextExtractor
from .navigation import SafeRedirectService
from .staff_portal import (
    StaffPortalContextService,
    StaffUserDirectory,
    UsageAnalytics,
)
from .usage import WebsiteUsageTracker

__all__ = (
    "ActivityRecorder",
    "AccountEmailPolicy",
    "CatalogQueryService",
    "ContactDeliveryError",
    "ContactEmailService",
    "DocumentExtractionError",
    "DocumentTextExtractor",
    "GreetingNameResolver",
    "PageContextBuilder",
    "SupportContactPresenter",
    "SafeRedirectService",
    "StaffPortalContextService",
    "StaffUserDirectory",
    "UsageAnalytics",
    "WebsiteUsageTracker",
    "AIDetectionError",
    "AIDetectionService",
    "DesklibAcademicDetector",
    "VanguardDetector",
)
