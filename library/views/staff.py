"""Public import facade for administrator class-based views."""

from .staff_accounts import (
    StaffAccountEditView,
    StaffUserCreateView,
    StaffUserDeleteView,
)
from .staff_ai import StaffAIDetectionView
from .staff_crud import (
    StaffAnnouncementCreateView,
    StaffAnnouncementDeleteView,
    StaffAnnouncementEditView,
    StaffAnnouncementPublishView,
    StaffAnnouncementUnpublishView,
    StaffFormView,
    StaffItemCreateView,
    StaffItemDeleteView,
    StaffItemEditView,
)
from .staff_dashboard import StaffPortalView

__all__ = (
    "StaffAccountEditView",
    "StaffAIDetectionView",
    "StaffAnnouncementCreateView",
    "StaffAnnouncementDeleteView",
    "StaffAnnouncementEditView",
    "StaffAnnouncementPublishView",
    "StaffAnnouncementUnpublishView",
    "StaffFormView",
    "StaffItemCreateView",
    "StaffItemDeleteView",
    "StaffItemEditView",
    "StaffPortalView",
    "StaffUserCreateView",
    "StaffUserDeleteView",
)
