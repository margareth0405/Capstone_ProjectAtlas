"""Query and presentation services for the administrator dashboard."""

from datetime import date

from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Sum
from django.utils import timezone

from library.models import (
    ActivityLog,
    Announcement,
    ContactMessage,
    DownloadEvent,
    LibraryItem,
    Profile,
    WebsiteVisit,
)


class StaffUserDirectory:
    """Filter and sort staff-visible account records from request parameters."""

    valid_roles = {
        Profile.Role.STUDENT,
        Profile.Role.TEACHER,
        "administrator",
    }

    def __init__(self, parameters):
        self.parameters = parameters

    @property
    def query(self):
        return self.parameters.get("user_q", "").strip()

    @property
    def role(self):
        return self.parameters.get("user_role", "").strip()

    @property
    def sort(self):
        requested = self.parameters.get("user_sort", "newest")
        return requested if requested in {"newest", "oldest"} else "newest"

    def build(self):
        users = (
            get_user_model()
            .objects.select_related("profile")
            .annotate(download_total=Count("download_events", distinct=True))
        )
        if self.query:
            users = users.filter(
                Q(first_name__icontains=self.query)
                | Q(last_name__icontains=self.query)
                | Q(email__icontains=self.query)
                | Q(username__icontains=self.query)
            )
        if self.role == "administrator":
            users = users.filter(Q(is_staff=True) | Q(is_superuser=True))
        elif self.role in {Profile.Role.STUDENT, Profile.Role.TEACHER}:
            users = users.filter(
                is_staff=False,
                is_superuser=False,
                profile__role=self.role,
            )
        return users.order_by("date_joined" if self.sort == "oldest" else "-date_joined")


class UsageAnalytics:
    """Aggregate per-role website usage for one calendar date."""

    role_colors = {
        WebsiteVisit.Role.GUEST: "#d39b45",
        WebsiteVisit.Role.STUDENT: "#3d76b5",
        WebsiteVisit.Role.TEACHER: "#3f8a5a",
        WebsiteVisit.Role.ADMINISTRATOR: "#7b2033",
    }

    def __init__(self, requested_date=""):
        self.selected_date = self.parse_date(requested_date)

    @staticmethod
    def parse_date(requested_date):
        try:
            return date.fromisoformat(requested_date) if requested_date else timezone.localdate()
        except ValueError:
            return timezone.localdate()

    def visits(self):
        return WebsiteVisit.objects.select_related("user").filter(
            started_at__date=self.selected_date
        )

    def role_usage(self, visits):
        totals = {
            row["role"]: {
                "seconds": row["seconds"] or 0,
                "sessions": row["sessions"],
            }
            for row in visits.values("role").annotate(
                seconds=Sum("duration_seconds"),
                sessions=Count("id"),
            )
        }
        total_seconds = sum(value["seconds"] for value in totals.values())
        return [
            self._role_row(role, label, totals, total_seconds)
            for role, label in WebsiteVisit.Role.choices
        ]

    def _role_row(self, role, label, totals, total_seconds):
        seconds = totals.get(role, {}).get("seconds", 0)
        return {
            "role": role,
            "label": label,
            "seconds": seconds,
            "minutes": round(seconds / 60, 1),
            "sessions": totals.get(role, {}).get("sessions", 0),
            "percent": round(seconds * 100 / total_seconds, 1)
            if total_seconds
            else 0,
            "color": self.role_colors[role],
        }

    @staticmethod
    def chart_gradient(role_usage):
        cursor = 0
        stops = []
        for row in role_usage:
            if not row["percent"]:
                continue
            end = min(100, cursor + row["percent"])
            stops.append(f'{row["color"]} {cursor:.1f}% {end:.1f}%')
            cursor = end
        return (
            f"conic-gradient({', '.join(stops)})"
            if stops
            else "conic-gradient(#ded8d4 0 100%)"
        )


class StaffPortalContextService:
    """Build the non-form context required by the administrator homepage."""

    role_choices = (
        ("student", "Student"),
        ("teacher", "Teacher"),
        ("administrator", "Administrator"),
    )

    def __init__(self, request):
        self.request = request
        self.directory = StaffUserDirectory(request.GET)
        self.analytics = UsageAnalytics(
            request.GET.get("analytics_date", "").strip()
        )

    def build(self):
        users = self.directory.build()
        all_users = get_user_model().objects.select_related("profile")
        visits = self.analytics.visits()
        role_usage = self.analytics.role_usage(visits)
        return {
            "staff_stats": self._staff_stats(all_users),
            "items": LibraryItem.objects.order_by("-created_at"),
            "recent_items": LibraryItem.objects.order_by("-created_at")[:8],
            "announcements": Announcement.objects.all(),
            "recent_announcements": Announcement.objects.all()[:6],
            "users": users,
            "user_count": all_users.count(),
            "download_count": DownloadEvent.objects.count(),
            "message_count": ContactMessage.objects.filter(is_resolved=False).count(),
            "downloads": DownloadEvent.objects.select_related("user", "item")[:20],
            "activity_history": ActivityLog.objects.select_related("actor")[:60],
            "visit_history": visits.order_by("-last_seen_at")[:50],
            "role_usage": role_usage,
            "usage_chart_gradient": self.analytics.chart_gradient(role_usage),
            "analytics_date": self.analytics.selected_date.isoformat(),
            "selected_user_query": self.directory.query,
            "selected_user_role": self.directory.role,
            "selected_user_sort": self.directory.sort,
            "user_role_choices": self.role_choices,
        }

    @staticmethod
    def _staff_stats(users):
        return {
            "total_users": users.count(),
            "student_users": users.filter(
                profile__role=Profile.Role.STUDENT
            ).count(),
            "teacher_users": users.filter(
                profile__role=Profile.Role.TEACHER
            ).count(),
            "successful_logins": users.filter(last_login__isnull=False).count(),
        }
