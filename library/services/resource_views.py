"""Privacy-aware tracking for readers opening library resources."""

from datetime import timedelta

from django.utils import timezone

from library.models import ResourceViewEvent
from library.services.usage import WebsiteUsageTracker


class ResourceViewTracker:
    """Record one resource use per active browser session and resource."""

    deduplication_window = timedelta(minutes=15)
    model = ResourceViewEvent

    def record(self, request, item):
        if not request.session.session_key:
            request.session.save()

        now = timezone.now()
        user = request.user if request.user.is_authenticated else None
        role = WebsiteUsageTracker.role_for(user)
        recent = (
            self.model.objects.filter(
                item=item,
                session_key=request.session.session_key,
                user=user,
                last_viewed_at__gte=now - self.deduplication_window,
            )
            .order_by("-last_viewed_at")
            .first()
        )
        if recent:
            recent.role = role
            recent.ip_address = WebsiteUsageTracker.ip_address(request)
            recent.save(update_fields=("role", "ip_address", "last_viewed_at"))
            return recent

        return self.model.objects.create(
            item=item,
            user=user,
            session_key=request.session.session_key,
            role=role,
            ip_address=WebsiteUsageTracker.ip_address(request),
        )