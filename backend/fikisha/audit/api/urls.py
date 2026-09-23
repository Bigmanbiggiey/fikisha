from __future__ import annotations

from django.urls import path

from fikisha.audit.api import views

app_name = "audit"

urlpatterns = [
    path("audit/entries", views.AuditEntriesView.as_view(), name="entries"),
]
