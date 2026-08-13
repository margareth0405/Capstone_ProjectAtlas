from django.urls import path

from . import views


app_name = 'library'

urlpatterns = [
    path('robots.txt', views.robots_txt, name='robots_txt'),
    path('', views.landing, name='landing'),
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('guest/', views.guest_login, name='guest_login'),
    path('logout/', views.logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('library/', views.catalog, name='catalog'),
    path('library/<int:pk>/', views.item_detail, name='item_detail'),
    path('library/<int:pk>/favorite/', views.favorite_toggle, name='favorite_toggle'),
    path('library/<int:pk>/download/', views.download, name='download'),
    path('favorites/', views.favorites, name='favorites'),
    path('announcements/', views.announcements, name='announcements'),
    path('contact/', views.contact, name='contact'),
    path('staff/', views.staff_portal, name='staff_portal'),
    path('staff/library/add/', views.staff_item_create, name='staff_item_create'),
    path('staff/library/<int:pk>/edit/', views.staff_item_edit, name='staff_item_edit'),
    path('staff/library/<int:pk>/delete/', views.staff_item_delete, name='staff_item_delete'),
    path('staff/announcements/add/', views.staff_announcement_create, name='staff_announcement_create'),
    path('staff/announcements/<int:pk>/edit/', views.staff_announcement_edit, name='staff_announcement_edit'),
    path('staff/announcements/<int:pk>/delete/', views.staff_announcement_delete, name='staff_announcement_delete'),
    path('staff/users/add/', views.staff_user_create, name='staff_user_create'),
]
