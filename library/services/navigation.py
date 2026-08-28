"""Safe redirect helpers for user-provided next-page values."""

from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme


class SafeRedirectService:
    """Resolve a local next URL without allowing open redirects."""

    @staticmethod
    def resolve(request, fallback):
        candidate = request.POST.get("next") or request.GET.get("next")
        if candidate and url_has_allowed_host_and_scheme(
            candidate,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return candidate
        return reverse(fallback)
