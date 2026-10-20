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
        "admin/directory/businesses/<uuid:account_id>/record",
        views.BusinessRecordView.as_view(),
        name="business-record",
    ),
    path(
        "admin/directory/<str:kind>/<uuid:account_id>/contact",
        views.DirectoryContactView.as_view(),
        name="directory-contact",
    ),
    path("admin/interventions", views.InterventionsView.as_view(), name="interventions"),
    path(
        "admin/operators/<uuid:operator_id>/approve",
        views.ApproveOperatorView.as_view(),
        name="approve-operator",
    ),
    path("admin/config", views.ConfigView.as_view(), name="config"),
    path("admin/config/preview", views.ConfigPreviewView.as_view(), name="config-preview"),
    path("admin/commission", views.CommissionLedgerView.as_view(), name="commission"),
    path("admin/cargo-categories", views.CargoCategoryView.as_view(), name="cargo-categories"),
    path(
        "admin/cargo-categories/keywords",
        views.CargoKeywordView.as_view(),
        name="cargo-keywords",
    ),
    path(
        "admin/cargo-categories/uncategorised",
        views.CargoUncategorisedView.as_view(),
        name="cargo-uncategorised",
    ),
]
