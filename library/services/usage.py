"""Website visit tracking used by middleware and administrator analytics."""

from datetime import timedelta

from django.utils import timezone

from library.models import Profile, WebsiteVisit


class WebsiteUsageTracker:
    """Track approximate active time for an authenticated or guest session."""

    idle_limit = timedelta(minutes=15)
    model = WebsiteVisit

    def should_track(self, request):
        return (
            request.user.is_authenticated or request.session.get("guest_mode")
        ) and not request.path.startswith(("/static/", "/media/"))

    def track(self, request):
        if not self.should_track(request):
            return None
        if not request.session.session_key:
            request.session.save()

        now = timezone.now()
        user = request.user if request.user.is_authenticated else None
        role = self.role_for(user)
        visit = (
            self.model.objects.filter(
                session_key=request.session.session_key,
                user=user,
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
                ip_address=self.ip_address(request),
            )

        gap = max(0, int((now - visit.last_seen_at).total_seconds()))
        visit.duration_seconds += min(gap, int(self.idle_limit.total_seconds()))
        visit.last_seen_at = now
        visit.role = role
        visit.save(update_fields=("duration_seconds", "last_seen_at", "role"))
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
