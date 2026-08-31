"""Website visit tracking used by browser activity events and analytics."""

from datetime import datetime, time, timedelta

from django.utils import timezone

from library.models import Profile, WebsiteVisit


class WebsiteUsageTracker:
    """Track visible-page activity, unique navigations, and active sessions."""

    idle_limit = timedelta(minutes=15)
    model = WebsiteVisit

    def should_track(self, request):
        return (
            request.user.is_authenticated or request.session.get("guest_mode")
        ) and not request.path.startswith(("/static/", "/media/"))

    def track(self, request, *, page_view=False, page_path=""):
        if not self.should_track(request):
            return None
        if not request.session.session_key:
            request.session.save()

        now = timezone.now()
        local_day_start = timezone.make_aware(
            datetime.combine(timezone.localdate(now), time.min),
            timezone.get_current_timezone(),
        )
        user = request.user if request.user.is_authenticated else None
        role = self.role_for(user)
        path = (page_path or request.path)[:255] if page_view else ""
        visit = (
            self.model.objects.filter(
                session_key=request.session.session_key,
                user=user,
                started_at__gte=local_day_start,
                last_seen_at__gte=now - self.idle_limit,
            )
            .order_by("-last_seen_at")
            .first()
        )
        if visit is None:
            return self.model.objects.create(
                session_key=request.session.session_key,
                user=user,
                role=role,
                page_views=1 if page_view else 0,
                last_path=path,
                ip_address=self.ip_address(request),
            )

        gap = max(0, int((now - visit.last_seen_at).total_seconds()))
        visit.duration_seconds += min(gap, int(self.idle_limit.total_seconds()))
        visit.last_seen_at = now
        visit.role = role
        update_fields = ["duration_seconds", "last_seen_at", "role"]
        if page_view and path != visit.last_path:
            visit.page_views += 1
            visit.last_path = path
            update_fields.extend(("page_views", "last_path"))
        visit.save(update_fields=update_fields)
        return visit

    @staticmethod
    def role_for(user):
        if user is None:
            return WebsiteVisit.Role.GUEST
        if user.is_staff or user.is_superuser:
            return WebsiteVisit.Role.ADMINISTRATOR
        profile = getattr(user, "profile", None)
        return profile.role if profile else Profile.Role.STUDENT

    @staticmethod
    def ip_address(request):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        return (
            forwarded.split(",")[0].strip()
            if forwarded
            else request.META.get("REMOTE_ADDR") or None
        )