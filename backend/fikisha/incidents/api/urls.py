from __future__ import annotations

from django.urls import path

from fikisha.incidents.api import views

app_name = "incidents"

urlpatterns = [
    # ─── Incidents ───────────────────────────────────────────────────
    path(
        "jobs/<uuid:job_id>/incidents",
        views.IncidentCollectionView.as_view(),
        name="incident-collection",
    ),
    path(
        "incidents/<uuid:incident_id>", views.IncidentDetailView.as_view(), name="incident-detail"
    ),
    path(
        "incidents/<uuid:incident_id>/evidence",
        views.IncidentEvidenceView.as_view(),
        name="incident-evidence",
    ),
    path(
        "incidents/<uuid:incident_id>/statements",
        views.IncidentStatementView.as_view(),
        name="incident-statements",
    ),
    path(
        "incidents/<uuid:incident_id>/review",
        views.IncidentReviewView.as_view(),
        name="incident-review",
    ),
    path(
        "incidents/<uuid:incident_id>/amicable",
        views.IncidentAmicableView.as_view(),
        name="incident-amicable",
    ),
    path(
        "incidents/<uuid:incident_id>/escalate",
        views.IncidentEscalateView.as_view(),
        name="incident-escalate",
    ),
    # ─── Disputes ────────────────────────────────────────────────────
    path(
        "jobs/<uuid:job_id>/disputes",
        views.DisputeCollectionView.as_view(),
        name="dispute-collection",
    ),
    path("disputes/<uuid:dispute_id>", views.DisputeDetailView.as_view(), name="dispute-detail"),
    path(
        "disputes/<uuid:dispute_id>/resolve",
        views.DisputeResolveView.as_view(),
        name="dispute-resolve",
    ),
]
