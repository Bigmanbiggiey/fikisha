from __future__ import annotations

from django.urls import path

from fikisha.statements.api import views

app_name = "statements"

urlpatterns = [
    path("statements", views.MyStatementsView.as_view(), name="mine"),
    path("statements/<uuid:statement_id>", views.StatementDetailView.as_view(), name="detail"),
    path("jobs/<uuid:job_id>/earnings", views.JobEarningsView.as_view(), name="job-earnings"),
    path("admin/statements", views.AdminStatementsView.as_view(), name="admin-list"),
    path("admin/statements/run", views.AdminRunView.as_view(), name="admin-run"),
    path(
        "admin/statements/<uuid:statement_id>",
        views.AdminStatementDetailView.as_view(),
        name="admin-detail",
    ),
    path(
        "admin/statements/<uuid:statement_id>/payments",
        views.AdminPaymentsView.as_view(),
        name="admin-payments",
    ),
    path(
        "admin/statements/<uuid:statement_id>/payments/<uuid:payment_id>/reverse",
        views.AdminReversePaymentView.as_view(),
        name="admin-payment-reverse",
    ),
]
