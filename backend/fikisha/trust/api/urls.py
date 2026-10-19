from __future__ import annotations

from django.urls import path

from fikisha.trust.api import views

app_name = "trust"

urlpatterns = [
    path("operators/me/tier", views.MyTierView.as_view(), name="my-tier"),
    path("operators/<uuid:operator_id>/tier", views.OperatorTierView.as_view(), name="tier"),
    path(
        "admin/operators/<uuid:operator_id>/tier",
        views.SetTierView.as_view(),
        name="set-tier",
    ),
    path("admin/tier-proposals", views.TierProposalsView.as_view(), name="proposals"),
    path(
        "admin/tier-proposals/<uuid:change_id>/decision",
        views.DecideProposalView.as_view(),
        name="decide",
    ),
]
