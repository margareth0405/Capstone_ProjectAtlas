"""Authentication and account-management routes."""

from django.urls import path

from library import views


urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("guest/", views.GuestLoginView.as_view(), name="guest_login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path(
        "staff/users/add/",
        views.StaffUserCreateView.as_view(),
        name="staff_user_create",
    ),
    path(
        "staff/users/<int:pk>/delete/",
        views.StaffUserDeleteView.as_view(),
        name="staff_user_delete",
    ),
]
