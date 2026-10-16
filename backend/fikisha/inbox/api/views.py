"""Messages inbox API (Design Phase 7 10g, ADR-2D-37) — a thin adapter over
``fikisha.inbox.services``. Read-only apart from the caller's own read
markers; no message is ever created here."""

from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from fikisha.common.api import OrgApiView
from fikisha.inbox import services
from fikisha.inbox.api.serializers import MarkReadSerializer

#: Item kinds a client may filter by (``?kind=OFFER,INCIDENT``).
MESSAGE_KINDS = {"OFFER", "FIKISHA_UPDATE", "INCIDENT", "DISPUTE"}


class MessagesView(OrgApiView):
    """``GET /messages?kind=&cursor=&limit=`` → ``{data, page, unread_count}``.
    ``kind`` (comma-separated) filters before paging, so a filter sees the
    whole inbox, not only the pages already loaded (PR #5 follow-up 3).
    ``unread_count`` always covers the whole inbox (for the navigation
    badge). Paging is forward-only: ``prev_cursor`` is always null."""

    action_get = "inbox.read"

    def get(self, request: Request) -> Response:
        items = services.conversations_for(self.actor(request))
        kinds = {k for k in (request.query_params.get("kind") or "").split(",") if k}
        if kinds - MESSAGE_KINDS:
            raise ValidationError({"kind": [f"Use any of {', '.join(sorted(MESSAGE_KINDS))}."]})
        shown = [i for i in items if i["kind"] in kinds] if kinds else items
        limit_raw = request.query_params.get("limit")
        limit = int(limit_raw) if limit_raw and limit_raw.isdigit() else None
        chunk, next_cursor = services.page(
            shown, cursor=request.query_params.get("cursor"), limit=limit
        )
        return Response(
            {
                "data": chunk,
                "page": {"next_cursor": next_cursor, "prev_cursor": None},
                "unread_count": sum(1 for i in items if i["unread"]),
            }
        )


class MessagesReadView(OrgApiView):
    """``POST /messages/read {conversation_key}`` → 204. Marks the caller's
    own conversation read up to now; idempotent by nature."""

    action_post = "inbox.mark_read"

    def post(self, request: Request) -> Response:
        serializer = MarkReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.mark_read(
            actor=self.actor(request),
            conversation_key=serializer.validated_data["conversation_key"],
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
