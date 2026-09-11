from __future__ import annotations

from django.urls import path

from fikisha.negotiation.api import views

app_name = "negotiation"

urlpatterns = [
    path(
        "jobs/<uuid:job_id>/negotiation/threads",
        views.NegotiationThreadCollectionView.as_view(),
        name="thread-collection",
    ),
    path(
        "negotiation/threads/<uuid:thread_id>",
        views.NegotiationThreadDetailView.as_view(),
        name="thread-detail",
    ),
    path(
        "negotiation/threads/<uuid:thread_id>/counter",
        views.NegotiationCounterView.as_view(),
        name="thread-counter",
    ),
    path(
        "negotiation/threads/<uuid:thread_id>/accept",
        views.NegotiationAcceptView.as_view(),
        name="thread-accept",
    ),
    path(
        "negotiation/threads/<uuid:thread_id>/decline",
        views.NegotiationDeclineView.as_view(),
        name="thread-decline",
    ),
]
