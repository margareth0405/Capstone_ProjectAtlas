"""Build the navigation and summary context used across ATLAS pages."""

from django.db.models import Count, Sum

from library.models import Favorite, LibraryItem, Profile


class GreetingNameResolver:
    """Return a friendly account label without exposing a full email address."""

    fallback_label = "User"

    @classmethod
    def resolve(cls, user):
        username = (user.get_username() or "").strip()
        if username and "@" not in username:
            return username

        full_name = user.get_full_name().strip()
        if full_name:
            return full_name

        email = (user.email or username).strip()
        local_part = email.partition("@")[0].strip()
        return local_part or cls.fallback_label


class PageContextBuilder:
    """Create shared template context for one request."""

    greeting_name_resolver_class = GreetingNameResolver

    def __init__(self, request):
        self.request = request

    def build(self, active_page):
        stats = self._stats()
        return {
            "active_page": active_page,
            "active_role": self._active_role(),
            "display_name": self._display_name(),
            "favorite_count": self._favorite_count(),
            "resource_count": stats["total_items"],
            "item_count": stats["total_items"],
            "collection_count": stats["unique_types"],
            "author_count": stats["unique_authors"],
            "stats": stats,
        }

    def _active_role(self):
        user = self.request.user
        if not user.is_authenticated:
            return "guest"
        if user.is_staff or user.is_superuser:
            return "administrator"
        profile = getattr(user, "profile", None)
        return profile.role if profile else Profile.Role.STUDENT

    def _display_name(self):
        user = self.request.user
        if not user.is_authenticated:
            return "Guest"
        return self.greeting_name_resolver_class.resolve(user)

    def _favorite_count(self):
        user = self.request.user
        if user.is_authenticated and not user.is_staff:
            return Favorite.objects.filter(user=user).count()
        return 0

    @staticmethod
    def _stats():
        stats = LibraryItem.objects.aggregate(
            total_items=Count("id"),
            total_pages=Sum("pages"),
            unique_authors=Count("author", distinct=True),
            unique_types=Count("collection", distinct=True),
        )
        stats["total_pages"] = stats["total_pages"] or 0
        return stats
