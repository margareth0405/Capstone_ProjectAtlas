"""Authentication and account-management routes."""

from django.urls import path

from library import views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("guest/", views.GuestLoginView.as_view(), name="guest_login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path(
        "staff/account/",
        views.StaffAccountEditView.as_view(),
        name="staff_account_edit",
    ),
    path(
        "staff/users/add/",
        views.StaffUserCreateView.as_view(),
        name="staff_user_create",
    ),
    path(
        "staff/administrators/add/",
        views.SuperuserAdminCreateView.as_view(),
        name="superuser_admin_create",
    ),
    path(
        "staff/users/<int:pk>/edit/",
        views.StaffAccountEditView.as_view(),
        name="staff_admin_edit",
    ),
    path(
        "staff/users/<int:pk>/delete/",
        views.StaffUserDeleteView.as_view(),
        name="staff_user_delete",
    ),
]
