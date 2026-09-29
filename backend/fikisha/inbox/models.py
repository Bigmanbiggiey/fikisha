"""Messages inbox (Design Phase 7 sub-increment 10g, ADR-2D-37).

The inbox stores **no messages**: every item is composed on read from the
records that already exist (negotiation entries, Fikisha notes, incident
statements, disputes). The only state it owns is how far each person has
read each conversation.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models

from fikisha.common.models import TimestampedModel


class InboxReadMarker(TimestampedModel):
    """ "This person has read this conversation up to ``last_read_at``."
    ``conversation_key`` is ``<kind>:<uuid>`` (``offer:``, ``notes:``,
    ``incident:``, ``dispute:``). Mutable by design: marking read again moves
    it forward. Not audited: it records what a person has looked at, not a
    sensitive change."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    conversation_key = models.CharField(max_length=64)
    last_read_at = models.DateTimeField()

    class Meta:
        db_table = "inbox_read_marker"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "conversation_key"], name="uq_inbox_read_marker_user_key"
            ),
        ]

    def __str__(self) -> str:  # pragma: no cover - debug aid
        return f"{self.user_id} read {self.conversation_key} at {self.last_read_at}"
