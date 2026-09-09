from __future__ import annotations

from django.urls import path

from fikisha.vehicles.api import views

app_name = "vehicles"

urlpatterns = [
    path("vehicles", views.VehicleCollectionView.as_view(), name="collection"),
    path("vehicles/<uuid:vehicle_id>", views.VehicleDetailView.as_view(), name="detail"),
    path(
        "vehicles/<uuid:vehicle_id>/status",
        views.VehicleStatusView.as_view(),
        name="status",
    ),
]
