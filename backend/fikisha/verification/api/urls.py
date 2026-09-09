from __future__ import annotations

from django.urls import path

from fikisha.verification.api import views

app_name = "verification"

urlpatterns = [
    path("verification/records", views.RecordCollectionView.as_view(), name="records"),
    path(
        "verification/records/<uuid:record_id>",
        views.RecordDetailView.as_view(),
        name="record-detail",
    ),
    path(
        "verification/records/<uuid:record_id>/evidence",
        views.RecordEvidenceView.as_view(),
        name="record-evidence",
    ),
    path(
        "verification/records/<uuid:record_id>/submit",
        views.RecordSubmitView.as_view(),
        name="record-submit",
    ),
    path(
        "verification/records/<uuid:record_id>/review/start",
        views.ReviewStartView.as_view(),
        name="review-start",
    ),
    path(
        "verification/records/<uuid:record_id>/review/request-info",
        views.ReviewRequestInfoView.as_view(),
        name="review-request-info",
    ),
    path(
        "verification/records/<uuid:record_id>/review/approve",
        views.ReviewApproveView.as_view(),
        name="review-approve",
    ),
    path(
        "verification/records/<uuid:record_id>/review/reject",
        views.ReviewRejectView.as_view(),
        name="review-reject",
    ),
    path("verification/queue", views.QueueView.as_view(), name="queue"),
    path(
        "verification/subjects/<str:subject_type>/<uuid:subject_id>/status",
        views.SubjectStatusView.as_view(),
        name="subject-status",
    ),
    path(
        "verification/evidence/<uuid:evidence_id>/content",
        views.EvidenceContentView.as_view(),
        name="evidence-content",
    ),
]
