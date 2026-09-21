from __future__ import annotations

from django.urls import path

from fikisha.jobs.api import views

app_name = "jobs"

urlpatterns = [
    # ─── Jobs ────────────────────────────────────────────────────────
    path("jobs", views.JobCollectionView.as_view(), name="collection"),
    path("jobs/opportunities", views.JobOpportunitiesView.as_view(), name="opportunities"),
    path(
        "jobs/<uuid:job_id>/opportunity",
        views.JobOpportunityDetailView.as_view(),
        name="opportunity-detail",
    ),
    path("jobs/<uuid:job_id>", views.JobDetailView.as_view(), name="detail"),
    path("jobs/<uuid:job_id>/submit", views.JobSubmitView.as_view(), name="submit"),
    path("jobs/<uuid:job_id>/cancel", views.JobCancelView.as_view(), name="cancel"),
    path(
        "jobs/<uuid:job_id>/assignment-candidates",
        views.JobAssignmentCandidatesView.as_view(),
        name="assignment-candidates",
    ),
    path("jobs/<uuid:job_id>/assign", views.JobAssignView.as_view(), name="assign"),
    path("jobs/<uuid:job_id>/commission", views.JobCommissionView.as_view(), name="commission"),
    # ─── Custody ─────────────────────────────────────────────────────
    path(
        "jobs/<uuid:job_id>/custody/arrive-pickup",
        views.ArriveAtPickupView.as_view(),
        name="arrive-pickup",
    ),
    path(
        "jobs/<uuid:job_id>/custody/confirm-pickup/otp",
        views.ConfirmPickupOtpView.as_view(),
        name="confirm-pickup-otp",
    ),
    path(
        "jobs/<uuid:job_id>/custody/confirm-pickup/business",
        views.ConfirmPickupByBusinessView.as_view(),
        name="confirm-pickup-business",
    ),
    path(
        "jobs/<uuid:job_id>/custody/confirm-pickup/attested",
        views.ConfirmPickupAttestedView.as_view(),
        name="confirm-pickup-attested",
    ),
    path(
        "jobs/<uuid:job_id>/custody/fail-at-pickup",
        views.FailAtPickupView.as_view(),
        name="fail-at-pickup",
    ),
    path(
        "jobs/<uuid:job_id>/custody/start-transit",
        views.StartTransitView.as_view(),
        name="start-transit",
    ),
    path(
        "jobs/<uuid:job_id>/custody/arrive-destination",
        views.ArriveAtDestinationView.as_view(),
        name="arrive-destination",
    ),
    path(
        "jobs/<uuid:job_id>/custody/confirm-delivery",
        views.ConfirmDeliveryView.as_view(),
        name="confirm-delivery",
    ),
    # ─── Recipient scoped access (bearer token in the URL) ──────────
    path("r/<str:token>", views.RecipientDetailView.as_view(), name="recipient-detail"),
    path("r/<str:token>/confirm", views.RecipientConfirmView.as_view(), name="recipient-confirm"),
    path(
        "r/<str:token>/report-issue",
        views.RecipientReportIssueView.as_view(),
        name="recipient-report-issue",
    ),
]
