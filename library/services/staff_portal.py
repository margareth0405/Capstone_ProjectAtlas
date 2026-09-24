"""Query and presentation services for the administrator dashboard."""

import logging
from datetime import date, datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import DatabaseError
from django.db.models import Count, IntegerField, Q, Sum, Value
from django.utils import timezone

from library.models import (
    ActivityLog,
    Announcement,
    ContactMessage,
    LibraryItem,
    Profile,
    ResourceViewEvent,
    WebsiteVisit,
)

logger = logging.getLogger(__name__)


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

    def build(self, *, include_profiles=True, include_view_totals=True):
        users = get_user_model().objects.all()
        if include_profiles:
            users = users.select_related("profile")
        if include_view_totals:
            users = users.annotate(
                resource_view_total=Count("resource_view_events", distinct=True)
            )
        else:
            users = users.annotate(
                resource_view_total=Value(0, output_field=IntegerField())
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
            users = users.filter(is_staff=False, is_superuser=False)
            if include_profiles:
                users = users.filter(profile__role=self.role)
        return users.order_by("date_joined" if self.sort == "oldest" else "-date_joined")

    def load(self):
        """Evaluate accounts with fallbacks for optional dashboard relations."""

        try:
            return self._decorate(list(self.build()), profiles_available=True)
        except DatabaseError:
            logger.exception(
                "Staff user directory could not load resource-view totals; "
                "retrying without them"
            )
        try:
            return self._decorate(
                list(self.build(include_view_totals=False)),
                profiles_available=True,
            )
        except DatabaseError:
            logger.exception(
                "Staff user directory could not load profiles; retrying with "
                "core account fields"
            )
        return self._decorate(
            list(
                self.build(
                    include_profiles=False,
                    include_view_totals=False,
                )
            ),
            profiles_available=False,
        )

    @staticmethod
    def _decorate(users, *, profiles_available):
        for account in users:
            if account.is_staff or account.is_superuser:
                account.atlas_role = "administrator"
                account.atlas_role_label = "Administrator"
                continue
            profile = None
            if profiles_available:
                try:
                    profile = account.profile
                except ObjectDoesNotExist:
                    pass
            account.atlas_role = (
                profile.role if profile is not None else Profile.Role.STUDENT
            )
            account.atlas_role_label = (
                profile.get_role_display() if profile is not None else "Student"
            )
        return users


class UsageAnalytics:
    """Aggregate and filter website usage for one local calendar date."""

    role_colors = {
        WebsiteVisit.Role.GUEST: "#d39b45",
        WebsiteVisit.Role.STUDENT: "#3d76b5",
        WebsiteVisit.Role.TEACHER: "#3f8a5a",
        WebsiteVisit.Role.ADMINISTRATOR: "#7b2033",
    }

    def __init__(self, parameters):
        self.parameters = parameters
        self.selected_date = self.parse_date(parameters.get("analytics_date", "").strip())

    @property
    def query(self):
        return self.parameters.get("usage_q", "").strip()

    @property
    def role(self):
        requested = self.parameters.get("usage_role", "").strip()
        valid = {value for value, _label in WebsiteVisit.Role.choices}
        return requested if requested in valid else ""

    @staticmethod
    def parse_date(requested_date):
        try:
            return date.fromisoformat(requested_date) if requested_date else timezone.localdate()
        except ValueError:
            return timezone.localdate()

    def visits(self):
        current_timezone = timezone.get_current_timezone()
        day_start = timezone.make_aware(
            datetime.combine(self.selected_date, time.min),
            current_timezone,
        )
        day_end = day_start + timedelta(days=1)
        return WebsiteVisit.objects.select_related("user").filter(
            started_at__gte=day_start,
            started_at__lt=day_end,
        )

    def filtered_visits(self, visits):
        filtered = visits
        if self.role:
            filtered = filtered.filter(role=self.role)
        if self.query:
            filtered = filtered.filter(
                Q(user__first_name__icontains=self.query)
                | Q(user__last_name__icontains=self.query)
                | Q(user__email__icontains=self.query)
                | Q(user__username__icontains=self.query)
                | Q(session_key__icontains=self.query)
            )
        return filtered

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
    def summary(visits):
        totals = visits.aggregate(
            total_seconds=Sum("duration_seconds"),
            total_page_views=Sum("page_views"),
            sessions=Count("id"),
            signed_in_users=Count("user", distinct=True),
        )
        guest_visitors = (
            visits.filter(user__isnull=True)
            .values("session_key")
            .distinct()
            .count()
        )
        return {
            "minutes": round((totals["total_seconds"] or 0) / 60, 1),
            "page_views": totals["total_page_views"] or 0,
            "sessions": totals["sessions"] or 0,
            "visitors": (totals["signed_in_users"] or 0) + guest_visitors,
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


class ResourceViewDirectory:
    """Search and filter staff-visible resource-reading history."""

    def __init__(self, parameters):
        self.parameters = parameters

    @property
    def query(self):
        return self.parameters.get("resource_view_q", "").strip()

    @property
    def role(self):
        requested = self.parameters.get("resource_view_role", "").strip()
        valid = {value for value, _label in WebsiteVisit.Role.choices}
        return requested if requested in valid else ""

    def build(self):
        events = ResourceViewEvent.objects.select_related("item", "user")
        if self.role:
            events = events.filter(role=self.role)
        if self.query:
            events = events.filter(
                Q(item__title__icontains=self.query)
                | Q(item__call_number__icontains=self.query)
                | Q(user__first_name__icontains=self.query)
                | Q(user__last_name__icontains=self.query)
                | Q(user__email__icontains=self.query)
            )
        return events


class StaffPortalContextService:
    """Build the non-form context required by the administrator homepage."""

    account_role_choices = (
        ("student", "Student"),
        ("teacher", "Teacher"),
        ("administrator", "Administrator"),
    )
    usage_role_choices = WebsiteVisit.Role.choices

    def __init__(self, request):
        self.request = request
        self.directory = StaffUserDirectory(request.GET)
        self.analytics = UsageAnalytics(request.GET)
        self.resource_views = ResourceViewDirectory(request.GET)

    def build(self):
        users = self.directory.load()
        all_users = get_user_model().objects.select_related("profile")
        analytics_context = self._analytics_context()
        return {
            "staff_stats": self._safe_staff_stats(all_users),
            "items": LibraryItem.objects.order_by("-created_at"),
            "recent_items": LibraryItem.objects.order_by("-created_at")[:8],
            "announcements": Announcement.objects.all(),
            "recent_announcements": Announcement.objects.all()[:6],
            "users": users,
            "user_count": all_users.count(),
            "resource_view_count": self._optional_database_value(
                "resource-view count",
                ResourceViewEvent.objects.count,
                0,
            ),
            "message_count": ContactMessage.objects.filter(is_resolved=False).count(),
            "resource_view_history": self._optional_database_value(
                "resource-view history",
                lambda: list(self.resource_views.build()[:50]),
                [],
            ),
            "activity_history": self._optional_database_value(
                "activity history",
                lambda: list(ActivityLog.objects.select_related("actor")[:60]),
                [],
            ),
            "visit_history": analytics_context["visit_history"],
            "role_usage": analytics_context["role_usage"],
            "usage_summary": analytics_context["usage_summary"],
            "usage_chart_gradient": self.analytics.chart_gradient(
                analytics_context["role_usage"]
            ),
            "analytics_date": self.analytics.selected_date.isoformat(),
            "selected_usage_query": self.analytics.query,
            "selected_usage_role": self.analytics.role,
            "selected_resource_view_query": self.resource_views.query,
            "selected_resource_view_role": self.resource_views.role,
            "selected_user_query": self.directory.query,
            "selected_user_role": self.directory.role,
            "selected_user_sort": self.directory.sort,
            "user_role_choices": self.account_role_choices,
            "usage_role_choices": self.usage_role_choices,
        }

    @staticmethod
    def _optional_database_value(label, operation, default):
        try:
            return operation()
        except DatabaseError:
            logger.exception("Staff dashboard could not load %s", label)
            return default

    def _analytics_context(self):
        try:
            visits = self.analytics.visits()
            role_usage = self.analytics.role_usage(visits)
            usage_summary = self.analytics.summary(visits)
            visit_history = list(
                self.analytics.filtered_visits(visits).order_by("-last_seen_at")[:50]
            )
        except DatabaseError:
            logger.exception("Staff dashboard could not load website usage analytics")
            role_usage = [
                self.analytics._role_row(role, label, {}, 0)
                for role, label in WebsiteVisit.Role.choices
            ]
            usage_summary = {
                "minutes": 0,
                "page_views": 0,
                "sessions": 0,
                "visitors": 0,
            }
            visit_history = []
        return {
            "role_usage": role_usage,
            "usage_summary": usage_summary,
            "visit_history": visit_history,
        }

    def _safe_staff_stats(self, users):
        try:
            return self._staff_stats(users)
        except DatabaseError:
            logger.exception("Staff dashboard could not load profile statistics")
            core_users = get_user_model().objects.all()
            return {
                "total_users": core_users.count(),
                "student_users": 0,
                "teacher_users": 0,
                "successful_logins": core_users.filter(
                    last_login__isnull=False
                ).count(),
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
