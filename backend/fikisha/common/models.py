"""Base model building blocks shared across bounded modules."""

from __future__ import annotations

from typing import Any, NoReturn

from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models.expressions import RawSQL

from fikisha.common.uuid7 import uuid7


def db_sequence_default(sequence_name: str) -> RawSQL:
    """A ``db_default`` expression drawing from a Postgres sequence the
    caller's migration creates (``CREATE SEQUENCE <sequence_name>``) — a
    strictly-monotonic, DB-assigned insertion-order tiebreaker for tables
    where two rows can otherwise tie: `created_at` (`auto_now_add`'s clock
    resolution) and `id` (UUIDv7, only time-ordered at millisecond
    granularity) are not reliable orderings under rapid successive writes.
    """
    # `sequence_name` is always a hardcoded literal supplied by our own model
    # definitions, never external input — no injection surface.
    return RawSQL(f"nextval('{sequence_name}')", [])  # noqa: S611


class UUIDPrimaryKeyModel(models.Model):
    """Abstract base: a time-ordered, non-guessable UUIDv7 primary key.

    Non-sequential ids are part of the IDOR/BOLA defence
    (docs/phase-1/security-architecture.md §1.10).
    """

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    class Meta:
        abstract = True


class TimestampedModel(UUIDPrimaryKeyModel):
    """Abstract base for mutable rows: adds created/updated timestamps."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AppendOnlyModelError(PermissionDenied):
    """Raised when application code attempts to mutate or delete an append-only row."""


class AppendOnlyModel(UUIDPrimaryKeyModel):
    """Abstract base for append-only rows (audit, outbox, config versions, ...).

    Enforced at three layers (docs/phase-1/database-design.md §1):
      1. the service layer exposes no update/delete path,
      2. **this model** raises on any update or delete from ORM code,
      3. in production the ``app_rw`` DB role has ``SELECT, INSERT`` only
         (see docs/phase-2/security-baseline.md — enforced by migration/SQL).
    """

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        abstract = True

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self._state.adding is False:
            raise AppendOnlyModelError(
                f"{type(self).__name__} is append-only; rows cannot be updated."
            )
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> NoReturn:
        raise AppendOnlyModelError(f"{type(self).__name__} is append-only; rows cannot be deleted.")


class AppendOnlyQuerySet(models.QuerySet):
    """QuerySet that refuses bulk update/delete for append-only tables."""

    def update(self, **kwargs: Any) -> NoReturn:
        raise AppendOnlyModelError(
            f"{self.model.__name__} is append-only; .update() is not allowed."
        )

    def delete(self) -> NoReturn:
        raise AppendOnlyModelError(
            f"{self.model.__name__} is append-only; .delete() is not allowed."
        )
