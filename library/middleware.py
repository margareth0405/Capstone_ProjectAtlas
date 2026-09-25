"""Application middleware kept thin by delegating to service objects."""

import logging
import time
from typing import ClassVar

from django.conf import settings
from django.core.cache import cache
from django.core.signing import salted_hmac
from django.shortcuts import render

from library.services.usage import WebsiteUsageTracker

logger = logging.getLogger(__name__)


class RateLimitMiddleware:
    """Apply endpoint-specific fixed-window limits to abuse-sensitive work.

    Ordinary page views are deliberately not counted. Schools commonly put many
    readers behind one public IP address, so a site-wide IP bucket can lock out
    an entire campus during normal repository use.
    """

    login_routes: ClassVar[set[str]] = {
        "library:login",
        "admin:login",
        "account_login",
    }

    post_rules: ClassVar[dict[str, tuple[str, str, str, str]]] = {
        "library:register": (
            "register",
            "RATE_LIMIT_REGISTER_REQUESTS",
            "RATE_LIMIT_REGISTER_WINDOW",
            "account",
        ),
        "library:contact": (
            "contact",
            "RATE_LIMIT_CONTACT_REQUESTS",
            "RATE_LIMIT_CONTACT_WINDOW",
            "account",
        ),
        "account_reset_password": (
            "email",
            "RATE_LIMIT_EMAIL_REQUESTS",
            "RATE_LIMIT_EMAIL_WINDOW",
            "account",
        ),
        "account_email": (
            "email",
            "RATE_LIMIT_EMAIL_REQUESTS",
            "RATE_LIMIT_EMAIL_WINDOW",
            "account",
        ),
        "library:staff_ai_detection": (
            "ai",
            "RATE_LIMIT_AI_REQUESTS",
            "RATE_LIMIT_AI_WINDOW",
            "user",
        ),
        "library:staff_item_create": (
            "upload",
            "RATE_LIMIT_UPLOAD_REQUESTS",
            "RATE_LIMIT_UPLOAD_WINDOW",
            "user",
        ),
        "library:staff_item_edit": (
            "upload",
            "RATE_LIMIT_UPLOAD_REQUESTS",
            "RATE_LIMIT_UPLOAD_WINDOW",
            "user",
        ),
    }

    staff_routes: ClassVar[set[str]] = {
        "library:staff_user_create",
        "library:staff_user_delete",
        "library:staff_item_delete",
        "library:staff_announcement_create",
        "library:staff_announcement_edit",
        "library:staff_announcement_publish",
        "library:staff_announcement_unpublish",
        "library:staff_announcement_delete",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        pending = getattr(request, "atlas_failed_login_rate_limit", None)
        if pending is not None and response.status_code == 200:
            scope, identifier, _limit, window = pending
            self._increment(scope, identifier, window)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Django supplies these positional callback details; rate limiting uses
        # the already-resolved route name on the request instead.
        del view_func, view_args, view_kwargs
        if not settings.RATE_LIMIT_ENABLED:
            return None

        view_name = getattr(request.resolver_match, "view_name", "")

        # Searching is the only public GET operation with a query-specific
        # allowance. Home, repository browsing, and resource viewing are never
        # placed in a restrictive shared-IP bucket.
        if (
            view_name == "library:catalog"
            and request.method == "GET"
            and request.GET.get("q", "").strip()
        ):
            return self._check(
                request,
                scope="search",
                identifier=self._identifier(request, strategy="visitor"),
                limit=settings.RATE_LIMIT_SEARCH_REQUESTS,
                window=settings.RATE_LIMIT_SEARCH_WINDOW,
            )

        if request.method != "POST":
            return None

        # Only unsuccessful authentication attempts consume the login budget.
        # The submitted account identifier prevents unrelated users behind the
        # same school router from sharing one allowance.
        if view_name in self.login_routes:
            identifier = self._identifier(request, strategy="account")
            limit = settings.RATE_LIMIT_LOGIN_REQUESTS
            window = settings.RATE_LIMIT_LOGIN_WINDOW
            response = self._blocked_response_if_at_limit(
                request,
                scope="login",
                identifier=identifier,
                limit=limit,
                window=window,
            )
            if response is None:
                request.atlas_failed_login_rate_limit = (
                    "login",
                    identifier,
                    limit,
                    window,
                )
            return response

        rule = self.post_rules.get(view_name)
        if rule is None and view_name in self.staff_routes:
            rule = (
                "staff",
                "RATE_LIMIT_STAFF_REQUESTS",
                "RATE_LIMIT_STAFF_WINDOW",
                "user",
            )
        if rule is None:
            return None
        scope, limit_setting, window_setting, strategy = rule
        return self._check(
            request,
            scope=scope,
            identifier=self._identifier(request, strategy=strategy),
            limit=getattr(settings, limit_setting),
            window=getattr(settings, window_setting),
        )

    @staticmethod
    def _identifier(request, *, strategy):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            value = f"user:{user.pk}"
        elif strategy == "account":
            account = (
                request.POST.get("email")
                or request.POST.get("username")
                or ""
            ).strip().casefold()
            value = (
                f"account:{account}"
                if account
                else RateLimitMiddleware._visitor_value(request)
            )
        else:
            value = RateLimitMiddleware._visitor_value(request)
        return salted_hmac("atlas.rate-limit-identity", value).hexdigest()

    @staticmethod
    def _visitor_value(request):
        session_key = getattr(getattr(request, "session", None), "session_key", None)
        if session_key:
            return f"session:{session_key}"
        address = request.META.get("REMOTE_ADDR", "unknown")
        if settings.RATE_LIMIT_TRUST_PROXY:
            forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
            if forwarded:
                address = forwarded.split(",", 1)[0].strip()
        return f"ip:{address}"

    @staticmethod
    def _cache_key(scope, identifier, window):
        window_id = int(time.time() // window)
        return f"atlas:rate:{scope}:{identifier}:{window_id}"

    def _blocked_response_if_at_limit(
        self, request, *, scope, identifier, limit, window
    ):
        if limit <= 0 or window <= 0:
            return None
        try:
            count = cache.get(self._cache_key(scope, identifier, window), 0)
        except Exception:
            logger.exception("Rate-limit cache unavailable; allowing request.")
            return None
        if count < limit:
            return None
        return self._limited_response(request, limit=limit, window=window)

    def _increment(self, scope, identifier, window):
        cache_key = self._cache_key(scope, identifier, window)
        try:
            if cache.add(cache_key, 1, timeout=window + 1):
                return 1
            return cache.incr(cache_key)
        except Exception:
            logger.exception("Rate-limit cache unavailable; allowing request.")
            return 0

    def _check(self, request, *, scope, identifier, limit, window):
        if limit <= 0 or window <= 0:
            return None
        count = self._increment(scope, identifier, window)
        if count <= limit:
            return None

        return self._limited_response(request, limit=limit, window=window)

    @staticmethod
    def _limited_response(request, *, limit, window):
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
