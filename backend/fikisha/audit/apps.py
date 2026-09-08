from __future__ import annotations

from django.apps import AppConfig


class AuditConfig(AppConfig):
    name = "fikisha.audit"
    label = "audit"
    verbose_name = "Fikisha · Audit"
