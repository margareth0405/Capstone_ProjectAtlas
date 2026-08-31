from django.urls import path

from . import views


app_name = 'library'

urlpatterns = [
    path("robots.txt", views.RobotsView.as_view(), name="robots_txt"),
    path("", views.LandingView.as_view(), name="landing"),
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("guest/", views.GuestLoginView.as_view(), name="guest_login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path(
        "usage/heartbeat/",
        views.UsageHeartbeatView.as_view(),
        name="usage_heartbeat",
    ),
    path("library/", views.CatalogView.as_view(), name="catalog"),
    path("library/<int:pk>/", views.ItemDetailView.as_view(), name="item_detail"),
    path(
        "library/<int:pk>/favorite/",
        views.FavoriteToggleView.as_view(),
        name="favorite_toggle",
    ),
    path("library/<int:pk>/download/", views.DownloadView.as_view(), name="download"),
    path("favorites/", views.FavoritesView.as_view(), name="favorites"),
    path("announcements/", views.AnnouncementsView.as_view(), name="announcements"),
    path("contact/", views.ContactView.as_view(), name="contact"),
    path("staff/", views.StaffPortalView.as_view(), name="staff_portal"),
    path(
        "staff/ai-detection/",
        views.StaffAIDetectionView.as_view(),
        name="staff_ai_detection",
    ),
    path(
        "staff/library/add/",
        views.StaffItemCreateView.as_view(),
        name="staff_item_create",
    ),
    path(
        "staff/library/<int:pk>/edit/",
        views.StaffItemEditView.as_view(),
        name="staff_item_edit",
    ),
    path(
        "staff/library/<int:pk>/delete/",
        views.StaffItemDeleteView.as_view(),
        name="staff_item_delete",
    ),
    path(
        "staff/announcements/add/",
        views.StaffAnnouncementCreateView.as_view(),
        name="staff_announcement_create",
    ),
    path(
        "staff/announcements/<int:pk>/edit/",
        views.StaffAnnouncementEditView.as_view(),
        name="staff_announcement_edit",
    ),
    path(
        "staff/announcements/<int:pk>/delete/",
        views.StaffAnnouncementDeleteView.as_view(),
        name="staff_announcement_delete",
    ),
    path(
        "staff/users/add/",
        views.StaffUserCreateView.as_view(),
        name="staff_user_create",
    ),
    path(
        "staff/users/<int:pk>/delete/",
        views.StaffUserDeleteView.as_view(),
        name="staff_user_delete",
    ),
    path(
        "staff/downloads/<int:pk>/delete/",
        views.StaffDownloadDeleteView.as_view(),
        name="staff_download_delete",
    ),
]
