"""Digital repository, bookmark, and resource-management routes."""

from django.urls import path

from library import views

urlpatterns = [
    path("repository/", views.CatalogView.as_view(), name="catalog"),
    path("repository/<int:pk>/", views.ItemDetailView.as_view(), name="item_detail"),
    path(
        "repository/<int:pk>/cover/",
        views.ResourceCoverView.as_view(),
        name="resource_cover",
    ),
    path(
        "repository/<int:pk>/resource-abstract/read/",
        views.ResourceAbstractReaderView.as_view(),
        name="resource_abstract_reader",
    ),
    path(
        "repository/<int:pk>/favorite/",
        views.FavoriteToggleView.as_view(),
        name="favorite_toggle",
    ),
    path("favorites/", views.FavoritesView.as_view(), name="favorites"),
    path(
        "staff/repository/add/",
        views.StaffItemCreateView.as_view(),
        name="staff_item_create",
    ),
    path(
        "staff/repository/<int:pk>/edit/",
        views.StaffItemEditView.as_view(),
        name="staff_item_edit",
    ),
    path(
        "staff/repository/<int:pk>/delete/",
        views.StaffItemDeleteView.as_view(),
        name="staff_item_delete",
    ),
]
