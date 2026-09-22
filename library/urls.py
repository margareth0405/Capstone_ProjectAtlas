from django.urls import include, path

from . import views


app_name = 'library'

urlpatterns = [
    # Domain routes live in dedicated apps while this namespace remains stable
    # for existing templates, redirects, and bookmarked URLs.
    path("", include("accounts.urls")),
    path("", include("repository.urls")),
    path("", include("ai_detection.urls")),
    path("health/", views.HealthCheckView.as_view(), name="health"),
    path("robots.txt", views.RobotsView.as_view(), name="robots_txt"),
    path("sitemap.xml", views.SitemapView.as_view(), name="sitemap"),
    path("", views.LandingView.as_view(), name="landing"),
    path("privacy-and-terms/", views.PrivacyTermsView.as_view(), name="privacy_terms"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path(
        "usage/heartbeat/",
        views.UsageHeartbeatView.as_view(),
        name="usage_heartbeat",
    ),
    path("announcements/", views.AnnouncementsView.as_view(), name="announcements"),
    path("contact/", views.ContactView.as_view(), name="contact"),
    path("staff/", views.StaffPortalView.as_view(), name="staff_portal"),
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
        "staff/announcements/<int:pk>/publish/",
        views.StaffAnnouncementPublishView.as_view(),
        name="staff_announcement_publish",
    ),
    path(
        "staff/announcements/<int:pk>/unpublish/",
        views.StaffAnnouncementUnpublishView.as_view(),
        name="staff_announcement_unpublish",
    ),
    path(
        "staff/announcements/<int:pk>/delete/",
        views.StaffAnnouncementDeleteView.as_view(),
        name="staff_announcement_delete",
    ),
]
