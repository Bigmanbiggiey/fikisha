from __future__ import annotations

from django.urls import path

from fikisha.operators.api import views

app_name = "operators"

urlpatterns = [
    path("operators", views.OperatorCollectionView.as_view(), name="collection"),
    path("operators/me", views.OperatorMeView.as_view(), name="me"),
    path("operators/<uuid:operator_id>", views.OperatorDetailView.as_view(), name="detail"),
    path(
        "operators/<uuid:operator_id>/bases",
        views.OperatorBaseCollectionView.as_view(),
        name="bases",
    ),
    path(
        "operators/<uuid:operator_id>/bases/<uuid:membership_id>",
        views.OperatorBaseDetailView.as_view(),
        name="base-detail",
    ),
    path(
        "operating-locations",
        views.OperatingLocationCollectionView.as_view(),
        name="operating-location-collection",
    ),
    path(
        "operating-locations/<uuid:base_id>",
        views.OperatingLocationDetailView.as_view(),
        name="operating-location-detail",
    ),
]
