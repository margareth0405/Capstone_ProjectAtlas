"""Public import facade for administrator class-based views."""

from .staff_accounts import (
    StaffAccountEditView,
    StaffUserCreateView,
    StaffUserDeleteView,
    SuperuserAdminCreateView,
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
from .staff_dashboard import StaffPortalView, StaffReportsView, StaffUsersView

__all__ = (
    "StaffAIDetectionView",
    "StaffAccountEditView",
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
    "StaffReportsView",
    "StaffUserCreateView",
    "StaffUserDeleteView",
    "StaffUsersView",
    "SuperuserAdminCreateView",
)
