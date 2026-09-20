"""Public sitemap definitions for search-engine discovery."""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from library.models import LibraryItem


class StaticPageSitemap(Sitemap):
    protocol = "https"
    changefreq = "weekly"
    priority = 0.6

    pages = (
        "library:landing",
        "library:catalog",
        "library:announcements",
        "library:contact",
        "library:privacy_terms",
    )

    def items(self):
        return self.pages

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return 1.0 if item == "library:landing" else 0.6


class LibraryItemSitemap(Sitemap):
    protocol = "https"
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        return LibraryItem.objects.only("pk", "updated_at").order_by("pk")

    def lastmod(self, item):
        return item.updated_at

    def location(self, item):
        return reverse("library:item_detail", args=(item.pk,))


sitemaps = {
    "pages": StaticPageSitemap,
    "library": LibraryItemSitemap,
}
