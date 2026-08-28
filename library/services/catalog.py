"""Catalog query construction kept separate from HTTP request handling."""

from django.db.models import Q

from library.models import LibraryItem


class CatalogQueryService:
    """Validate catalog inputs and build a consistently ordered queryset."""

    SORT_FIELDS = {
        "title": "title",
        "-title": "-title",
        "author": "author",
        "-author": "-author",
        "collection": "collection",
        "-collection": "-collection",
        "newest": "-created_at",
        "oldest": "created_at",
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
        return items.order_by(self.SORT_FIELDS.get(self.sort, "title"))
