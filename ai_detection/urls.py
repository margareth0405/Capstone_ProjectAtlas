"""Administrator AI-detection routes."""

from django.urls import path

from library import views

urlpatterns = [
    path(
        "staff/ai-detection/",
        views.StaffAIDetectionView.as_view(),
        name="staff_ai_detection",
    ),
]
