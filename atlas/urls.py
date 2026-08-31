"""Top-level URL configuration for ATLAS."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView


admin.site.site_header = "ATLAS Administration"
admin.site.site_title = "ATLAS Admin"
admin.site.index_title = "Library management"

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
    path("accounts/", include("allauth.urls")),
    path("", include("library.urls")),
]

if settings.DEBUG:
    urlpatterns += [
        path('__reload__/', include('django_browser_reload.urls')),
    ]
