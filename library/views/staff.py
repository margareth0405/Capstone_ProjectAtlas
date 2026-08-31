"""Public import facade for administrator class-based views."""

from .staff_accounts import (
    StaffDownloadDeleteView,
    StaffUserCreateView,
    StaffUserDeleteView,
)
from .staff_ai import StaffAIDetectionView
from .staff_crud import (
    StaffAnnouncementCreateView,
    StaffAnnouncementDeleteView,
    StaffAnnouncementEditView,
    StaffFormView,
    StaffItemCreateView,
    StaffItemDeleteView,
    StaffItemEditView,
)
from .staff_dashboard import StaffPortalView

__all__ = (
    "StaffAIDetectionView",
    "StaffAnnouncementCreateView",
    "StaffAnnouncementDeleteView",
    "StaffAnnouncementEditView",
    "StaffDownloadDeleteView",
    "StaffFormView",
    "StaffItemCreateView",
    "StaffItemDeleteView",
    "StaffItemEditView",
    "StaffPortalView",
    "StaffUserCreateView",
    "StaffUserDeleteView",
)
