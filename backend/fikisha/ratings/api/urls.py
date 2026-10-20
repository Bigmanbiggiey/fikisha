from __future__ import annotations

from django.urls import path

from fikisha.ratings.api import views

app_name = "ratings"

urlpatterns = [
    path("jobs/<uuid:job_id>/ratings", views.JobRatingsView.as_view(), name="job-ratings"),
]
