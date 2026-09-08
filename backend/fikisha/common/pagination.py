"""Cursor pagination (Phase 1 api-architecture §1: no offset pagination)."""

from __future__ import annotations

from typing import Any

from rest_framework.pagination import CursorPagination as DRFCursorPagination
from rest_framework.response import Response


class CursorPagination(DRFCursorPagination):
    page_size = 25
    max_page_size = 100
    page_size_query_param = "limit"
    cursor_query_param = "cursor"
    ordering = "-created_at"

    def get_paginated_response(self, data: Any) -> Response:
        return Response(
            {
                "data": data,
                "page": {
                    "next_cursor": self.get_next_link(),
                    "prev_cursor": self.get_previous_link(),
                },
            }
        )

    def get_paginated_response_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "data": schema,
                "page": {
                    "type": "object",
                    "properties": {
                        "next_cursor": {"type": "string", "nullable": True},
                        "prev_cursor": {"type": "string", "nullable": True},
                    },
                },
            },
        }
