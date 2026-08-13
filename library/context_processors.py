from django.conf import settings


def atlas_navigation(request):
    profile = None
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        profile = getattr(user, "profile", None)
    return {
        "atlas_profile": profile,
        "privacy_consent_version": getattr(
            settings, "PRIVACY_CONSENT_VERSION", "2026-08-11"
        ),
    }
