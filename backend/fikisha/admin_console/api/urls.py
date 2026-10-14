from __future__ import annotations

from django.urls import path

from fikisha.admin_console.api import views

app_name = "admin_console"

urlpatterns = [
    path("admin/directory/<str:kind>", views.DirectoryListView.as_view(), name="directory"),
    path(
        "admin/directory/<str:kind>/<uuid:account_id>",
        views.DirectoryDetailView.as_view(),
        name="directory-detail",
    ),
    path(
        "admin/directory/<str:kind>/<uuid:account_id>/contact",
        views.DirectoryContactView.as_view(),
        name="directory-contact",
    ),
    path("admin/interventions", views.InterventionsView.as_view(), name="interventions"),
    path("admin/config", views.ConfigView.as_view(), name="config"),
    path("admin/config/preview", views.ConfigPreviewView.as_view(), name="config-preview"),
    path("admin/commission", views.CommissionLedgerView.as_view(), name="commission"),
]
