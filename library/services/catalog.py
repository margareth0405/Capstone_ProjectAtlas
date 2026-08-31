"""Catalog query construction kept separate from HTTP request handling."""

from django.db.models import F, Q

from library.models import LibraryItem


class CatalogQueryService:
    """Validate catalog inputs and build a consistently ordered queryset."""

    SORT_FIELDS = {
        "title": ("title", "author"),
        "-title": ("-title", "author"),
        "author": ("author", "title"),
        "-author": ("-author", "title"),
        "published_newest": (F("published_on").desc(nulls_last=True), "title"),
        "published_oldest": (F("published_on").asc(nulls_last=True), "title"),
        # Retain old links while making their meaning publication-based.
        "newest": (F("published_on").desc(nulls_last=True), "title"),
        "oldest": (F("published_on").asc(nulls_last=True), "title"),
    }

    def __init__(self, parameters):
        self.query = parameters.get("q", "").strip()
        self.collection = parameters.get("collection", "").strip()
        self.sort = parameters.get("sort", "title")

    def build(self):
        items = LibraryItem.objects.all()
        if self.query:
            items = items.filter(
                Q(title__icontains=self.query)
                | Q(author__icontains=self.query)
                | Q(call_number__icontains=self.query)
                | Q(details__icontains=self.query)
            )
        valid_collections = {value for value, _label in LibraryItem.Collection.choices}
        if self.collection in valid_collections:
            items = items.filter(collection=self.collection)
        ordering = self.SORT_FIELDS.get(self.sort, self.SORT_FIELDS["title"])
        return items.order_by(*ordering)
