"""Feature-grouped class-based views for the ATLAS application."""

from .authentication import GuestLoginView, LandingView, LoginView, LogoutView, RegisterView
from .catalog import CatalogView, DownloadView, FavoriteToggleView, FavoritesView, ItemDetailView
from .public import (
    AnnouncementsView,
    ContactView,
    DashboardView,
    RobotsView,
    UsageHeartbeatView,
)
from .staff import (
    StaffAIDetectionView,
    StaffAnnouncementCreateView,
    StaffAnnouncementDeleteView,
    StaffAnnouncementEditView,
    StaffItemCreateView,
    StaffItemDeleteView,
    StaffItemEditView,
    StaffPortalView,
    StaffUserCreateView,
    StaffUserDeleteView,
    StaffDownloadDeleteView,
)

__all__ = tuple(name for name in globals() if name.endswith("View"))
