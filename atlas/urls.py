"""Top-level URL configuration for ATLAS."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from library.views import AccountSettingsView, PasswordResetView

admin.site.site_header = "ATLAS Administration"
admin.site.site_title = "ATLAS Admin"
admin.site.index_title = "Digital Sources management"

urlpatterns = [
    path(f"{settings.ADMIN_URL_PATH}/", admin.site.urls),
    # Keep allauth's account-management/recovery endpoints, but funnel its
    # alternate auth entry points through ATLAS's role/consent-aware screens.
    path(
        "accounts/login/",
        RedirectView.as_view(pattern_name="library:login", permanent=False),
    ),
    path(
        "accounts/signup/",
        RedirectView.as_view(pattern_name="library:register", permanent=False),
    ),
    path(
        "accounts/logout/",
        RedirectView.as_view(pattern_name="library:landing", permanent=False),
    ),
    path(
        "accounts/email/",
        AccountSettingsView.as_view(),
        name="account_email",
    ),
    path(
        "accounts/password/reset/",
        PasswordResetView.as_view(),
        name="account_reset_password",
    ),
    path("accounts/", include("allauth.urls")),
    path("", include("library.urls")),
]

if settings.DEBUG:
    urlpatterns += [
        path('__reload__/', include('django_browser_reload.urls')),
    ]

handler400 = "library.views.errors.bad_request"
handler403 = "library.views.errors.permission_denied"
handler404 = "library.views.errors.page_not_found"
handler500 = "library.views.errors.server_error"
