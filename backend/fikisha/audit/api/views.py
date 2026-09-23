"""Audit read API (Design Phase 6 Increment 8, P3 §18.5) — read-only;
"who acted · what happened · when · to which resource". Not an end-user
feature: gated on ``audit.view.scoped`` and scoped per
:mod:`fikisha.audit.scopes`."""

from __future__ import annotations

import uuid
from typing import Any

from django.utils.dateparse import parse_datetime
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response

from fikisha.audit.models import AuditLogEntry
from fikisha.audit.scopes import OPS_AUDIT_ENTITY_TYPES
from fikisha.common.api import OrgApiView
from fikisha.common.exceptions import DomainError
from fikisha.common.pagination import CursorPagination


class InvalidAuditFilter(DomainError):
    default_code = "invalid_filter"


class _AuditPagination(CursorPagination):
    ordering = "-seq"


class _AuditEntryRow(serializers.BaseSerializer):
    """Never ``source_ip`` / ``source_device`` (personal data, not needed to
    answer "who did what to which resource")."""

    def to_representation(self, entry: AuditLogEntry) -> dict[str, Any]:
        return {
            "seq": entry.seq,
            "server_time": entry.server_time.isoformat(),
            "actor_user_id": str(entry.actor_user_id) if entry.actor_user_id else None,
            "actor_role": entry.actor_role,
            "action": entry.action,
            "entity_type": entry.entity_type,
            "entity_id": str(entry.entity_id) if entry.entity_id else None,
            "before": entry.before,
            "after": entry.after,
            "source_channel": entry.source_channel,
        }


def _uuid_param(request: Request, name: str) -> uuid.UUID | None:
    raw = request.query_params.get(name)
    if not raw:
        return None
    try:
        return uuid.UUID(raw)
    except ValueError as exc:
        raise InvalidAuditFilter(f"{name} must be a UUID.") from exc


def _time_param(request: Request, name: str) -> Any:
    raw = request.query_params.get(name)
    if not raw:
        return None
    parsed = parse_datetime(raw)
    if parsed is None:
        raise InvalidAuditFilter(f"{name} must be an ISO-8601 date-time.")
    return parsed


class AuditEntriesView(OrgApiView):
    action_get = "audit.view.scoped"

    def get(self, request: Request) -> Response:
        qs = AuditLogEntry.objects.all()
        if not self.is_platform_admin(request):
            qs = qs.filter(entity_type__in=OPS_AUDIT_ENTITY_TYPES)

        params = request.query_params
        actor_user = _uuid_param(request, "actor_user")
        entity_id = _uuid_param(request, "entity_id")
        since, until = _time_param(request, "from"), _time_param(request, "to")
        if actor_user:
            qs = qs.filter(actor_user_id=actor_user)
        if params.get("entity_type"):
            qs = qs.filter(entity_type=params["entity_type"])
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        if params.get("action"):
            qs = qs.filter(action__startswith=params["action"])
        if since:
            qs = qs.filter(server_time__gte=since)
        if until:
            qs = qs.filter(server_time__lte=until)

        paginator = _AuditPagination()
        page = paginator.paginate_queryset(qs, request) or []
        return paginator.get_paginated_response(_AuditEntryRow(page, many=True).data)
