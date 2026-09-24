"""Application middleware kept thin by delegating to service objects."""

import logging
import time

from django.conf import settings
from django.core.cache import cache
from django.core.signing import salted_hmac
from django.shortcuts import render

from library.services.usage import WebsiteUsageTracker

logger = logging.getLogger(__name__)


class RateLimitMiddleware:
    """Apply privacy-safe fixed-window limits before a view does expensive work."""

    sensitive_rules = {
        "library:login": ("login", "RATE_LIMIT_LOGIN_REQUESTS", "RATE_LIMIT_LOGIN_WINDOW"),
        "admin:login": ("login", "RATE_LIMIT_LOGIN_REQUESTS", "RATE_LIMIT_LOGIN_WINDOW"),
        "account_login": ("login", "RATE_LIMIT_LOGIN_REQUESTS", "RATE_LIMIT_LOGIN_WINDOW"),
        "library:register": (
            "register",
            "RATE_LIMIT_REGISTER_REQUESTS",
            "RATE_LIMIT_REGISTER_WINDOW",
        ),
        "library:contact": (
            "contact",
            "RATE_LIMIT_CONTACT_REQUESTS",
            "RATE_LIMIT_CONTACT_WINDOW",
        ),
        "account_reset_password": (
            "email",
            "RATE_LIMIT_EMAIL_REQUESTS",
            "RATE_LIMIT_EMAIL_WINDOW",
        ),
        "account_email": (
            "email",
            "RATE_LIMIT_EMAIL_REQUESTS",
            "RATE_LIMIT_EMAIL_WINDOW",
        ),
        "library:staff_ai_detection": (
            "ai",
            "RATE_LIMIT_AI_REQUESTS",
            "RATE_LIMIT_AI_WINDOW",
        ),
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Django supplies these positional callback details; rate limiting uses
        # the already-resolved route name on the request instead.
        del view_func, view_args, view_kwargs
        if not settings.RATE_LIMIT_ENABLED:
            return None

        identifier = self._identifier(request)
        global_response = self._check(
            request,
            scope="global",
            identifier=identifier,
            limit=settings.RATE_LIMIT_GLOBAL_REQUESTS,
            window=settings.RATE_LIMIT_GLOBAL_WINDOW,
        )
        if global_response is not None:
            return global_response

        if request.method != "POST":
            return None
        view_name = getattr(request.resolver_match, "view_name", "")
        rule = self.sensitive_rules.get(view_name)
        if rule is None:
            return None
        scope, limit_setting, window_setting = rule
        return self._check(
            request,
            scope=scope,
            identifier=identifier,
            limit=getattr(settings, limit_setting),
            window=getattr(settings, window_setting),
        )

    @staticmethod
    def _identifier(request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            value = f"user:{user.pk}"
        else:
            address = request.META.get("REMOTE_ADDR", "unknown")
            if settings.RATE_LIMIT_TRUST_PROXY:
                forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
                if forwarded:
                    address = forwarded.split(",", 1)[0].strip()
            value = f"ip:{address}"
        return salted_hmac("atlas.rate-limit-identity", value).hexdigest()

    def _check(self, request, *, scope, identifier, limit, window):
        if limit <= 0 or window <= 0:
            return None
        window_id = int(time.time() // window)
        cache_key = f"atlas:rate:{scope}:{identifier}:{window_id}"
        try:
            if cache.add(cache_key, 1, timeout=window + 1):
                count = 1
            else:
                count = cache.incr(cache_key)
        except Exception:
            logger.exception("Rate-limit cache unavailable; allowing request.")
            return None
        if count <= limit:
            return None

        response = render(
            request,
            "errors/429.html",
            {"retry_after": window},
            status=429,
        )
        response["Retry-After"] = str(window)
        response["Cache-Control"] = "no-store"
        response["X-RateLimit-Limit"] = str(limit)
        return response


class WebsiteUsageMiddleware:
    """Persist only explicit visible-page events sent by the ATLAS browser UI."""

    tracker_class = WebsiteUsageTracker

    def __init__(self, get_response):
        self.get_response = get_response
        self.tracker = self.tracker_class()

    def __call__(self, request):
        response = self.get_response(request)
        event = getattr(request, "atlas_usage_event", "")
        if event:
            self.tracker.track(
                request,
                page_view=event == "page_view",
                page_path=getattr(request, "atlas_usage_page_path", ""),
            )
        return response
