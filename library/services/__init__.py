"""Application service objects shared by ATLAS views and middleware."""

from .accounts import AccountEmailPolicy
from .activity import ActivityRecorder
from .ai_detection import (
    AcademicBertDetector,
    AIDetectionError,
    AIDetectionService,
    DesklibAcademicDetector,
    FastWritingPatternDetector,
)
from .catalog import CatalogQueryService
from .contact import ContactDeliveryError, ContactEmailService
from .context import GreetingNameResolver, PageContextBuilder, SupportContactPresenter
from .documents import DocumentExtractionError, DocumentTextExtractor
from .navigation import SafeRedirectService
from .repository_items import RepositoryItemPersistenceService, ResourceStorageError
from .staff_portal import (
    StaffPortalContextService,
    StaffUserDirectory,
    UsageAnalytics,
)
from .usage import WebsiteUsageTracker

__all__ = (
    "AcademicBertDetector",
    "AIDetectionError",
    "AIDetectionService",
    "AccountEmailPolicy",
    "ActivityRecorder",
    "CatalogQueryService",
    "ContactDeliveryError",
    "ContactEmailService",
    "DesklibAcademicDetector",
    "DocumentExtractionError",
    "DocumentTextExtractor",
    "FastWritingPatternDetector",
    "GreetingNameResolver",
    "PageContextBuilder",
    "RepositoryItemPersistenceService",
    "ResourceStorageError",
    "SafeRedirectService",
    "StaffPortalContextService",
    "StaffUserDirectory",
    "SupportContactPresenter",
    "UsageAnalytics",
    "WebsiteUsageTracker",
)
