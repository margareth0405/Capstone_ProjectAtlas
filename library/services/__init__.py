"""Application service objects shared by ATLAS views and middleware."""

from .activity import ActivityRecorder
from .ai_detection import WritingPatternAnalyzer
from .catalog import CatalogQueryService
from .contact import ContactDeliveryError, ContactEmailService
from .context import GreetingNameResolver, PageContextBuilder
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
    "CatalogQueryService",
    "ContactDeliveryError",
    "ContactEmailService",
    "DocumentExtractionError",
    "DocumentTextExtractor",
    "GreetingNameResolver",
    "PageContextBuilder",
    "SafeRedirectService",
    "StaffPortalContextService",
    "StaffUserDirectory",
    "UsageAnalytics",
    "WebsiteUsageTracker",
    "WritingPatternAnalyzer",
)