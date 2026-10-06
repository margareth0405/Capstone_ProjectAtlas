"""Application service objects shared by ATLAS views and middleware."""

from .accounts import AccountEmailPolicy
from .activity import ActivityRecorder
from .ai_detection import (
    AIDetectionBenchmarkService,
    AIDetectionError,
    AIDetectionService,
    DesklibAcademicDetector,
    FastWritingPatternDetector,
    OnnxDistilBertDetector,
    RemoteDesklibDetector,
    VanguardAIDetector,
)
from .catalog import CatalogQueryService
from .contact import ContactDeliveryError, ContactEmailService
from .context import GreetingNameResolver, PageContextBuilder, SupportContactPresenter
from .documents import DocumentExtractionError, DocumentTextExtractor
from .navigation import SafeRedirectService
from .repository_items import RepositoryItemPersistenceService, ResourceStorageError
from .resource_review import (
    ResourceReviewAnalysisService,
    is_teacher,
    visible_library_items,
)
from .staff_portal import (
    StaffPortalContextService,
    StaffUserDirectory,
    UsageAnalytics,
)
from .usage import WebsiteUsageTracker

__all__ = (
    "AIDetectionBenchmarkService",
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
    "OnnxDistilBertDetector",
    "PageContextBuilder",
    "RemoteDesklibDetector",
    "RepositoryItemPersistenceService",
    "ResourceStorageError",
    "ResourceReviewAnalysisService",
    "SafeRedirectService",
    "StaffPortalContextService",
    "StaffUserDirectory",
    "SupportContactPresenter",
    "UsageAnalytics",
    "VanguardAIDetector",
    "WebsiteUsageTracker",
    "is_teacher",
    "visible_library_items",
)
