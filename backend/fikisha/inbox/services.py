"""Messages inbox composition (Design Phase 7 sub-increment 10g, ADR-2D-37).

One list of the conversations that **already exist** on a person's jobs,
newest first, with unread markers. Nothing is written here except read
markers: negotiation stays the authoritative record of offers, WhatsApp
stays a notification channel, and no new message channel is created.

Every source is read through its module's public surface (module boundary
rule), and each module applies its own party check:

* offers:   ``negotiation.services.inbox_threads_for_jobs`` (sealed threads)
* notes:    ``jobs.ops.notes_for_jobs`` on the jobs from
            ``jobs.job_authz.recent_jobs_visible_to`` that pass
            ``job_authz.is_job_party`` (the job-notes endpoint's ``job.read``
            rule; the visible-jobs list alone is wider)
* issues:   ``incidents.services.inbox_items_for_jobs`` (incident party rule)

Each source is one batch read across all the jobs, and the membership
lookups behind the party checks run under ``common.authz_memo``, so a request
costs a fixed number of queries rather than a few per job.

Staff get an empty inbox: they already work from the Ops queues, and their
admin visibility of every job must not turn into an inbox of every job.
"""

from __future__ import annotations

import base64
import binascii
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from django.utils import timezone
from rest_framework import status

from fikisha.common.authz_memo import authz_memo
from fikisha.common.exceptions import DomainError
from fikisha.inbox.models import InboxReadMarker

# The most recent jobs scanned per request. Enough for a pilot business or
# operator; beyond it, older jobs' conversations drop off the inbox (their
# screens are unaffected). Recorded in ADR-2D-37.
MAX_JOBS = 200
PAGE_SIZE = 25
MAX_PAGE_SIZE = 100

KINDS = ("offer", "notes", "incident", "dispute")
_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
_KEY = re.compile(rf"^(offer|notes|incident|dispute):{_UUID}$")


class InvalidConversationKey(DomainError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "inbox_invalid_conversation_key"
    default_detail = "That is not a conversation key."


class InvalidCursor(DomainError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "inbox_invalid_cursor"
    default_detail = "That page cursor is not valid."


@dataclass
class _Item:
    key: str
    at: datetime
    by_viewer: bool
    payload: dict[str, Any]


def _user(actor: Any) -> Any:
    return getattr(actor, "user", None)


def _items_for_jobs(actor: Any, jobs: list[Any]) -> list[_Item]:
    """One batch read per source across all the jobs, then the items job by
    job. A fixed number of queries, not a few per job."""
    from fikisha.incidents import services as incidents_services
    from fikisha.jobs import job_authz
    from fikisha.jobs import ops as jobs_ops
    from fikisha.negotiation import services as negotiation_services

    threads = negotiation_services.inbox_threads_for_jobs(actor=actor, jobs=jobs)
    # ``jobs_visible_to`` is wider than ``job.read`` (it lists a business
    # VIEWER's or a non-managing group member's jobs), so the notes are
    # gated on the notes endpoint's own party rule, job by job.
    notes = jobs_ops.notes_for_jobs(
        [job.id for job in jobs if job_authz.is_job_party(actor, job)], staff=False
    )
    issues = incidents_services.inbox_items_for_jobs(actor=actor, jobs=jobs)

    items: list[_Item] = []
    for job in jobs:
        items.extend(
            _job_items(
                job,
                threads.get(str(job.id), []),
                notes.get(str(job.id), []),
                issues.get(str(job.id), []),
            )
        )
    return items


def _job_items(
    job: Any,
    threads: list[dict[str, Any]],
    notes: list[dict[str, Any]],
    issues: list[dict[str, Any]],
) -> list[_Item]:
    from fikisha.jobs import ops as jobs_ops

    base = {"job_id": str(job.id), "job_reference": jobs_ops.job_reference(job.id)}
    items: list[_Item] = []

    for thread in threads:
        latest = thread["latest"]
        items.append(
            _Item(
                key=f"offer:{thread['thread_id']}",
                at=latest["created_at"],
                by_viewer=latest["by_viewer"],
                payload={
                    **base,
                    "kind": "OFFER",
                    "link": f"/jobs/{job.id}/negotiation",
                    "counterparty_name": thread["counterparty_name"],
                    "thread_status": thread["status"],
                    "entry_type": latest["type"],
                    "amount_kes": latest["amount_kes"],
                    "from_viewer": latest["by_viewer"],
                    "from_fikisha": latest["by_fikisha"],
                    "preview": latest["note"],
                },
            )
        )

    if notes:
        last = notes[-1]
        items.append(
            _Item(
                key=f"notes:{job.id}",
                at=datetime.fromisoformat(last["created_at"]),
                by_viewer=False,
                payload={
                    **base,
                    "kind": "FIKISHA_UPDATE",
                    "link": f"/jobs/{job.id}",
                    "preview": last["text"],
                    "count": len(notes),
                },
            )
        )

    for row in issues:
        kind = row["kind"]
        items.append(
            _Item(
                key=f"{kind.lower()}:{row['id']}",
                at=row["at"],
                by_viewer=row["by_viewer"],
                payload={
                    **base,
                    "kind": kind,
                    "link": f"/{'incidents' if kind == 'INCIDENT' else 'disputes'}/{row['id']}",
                    "status": row["status"],
                    "incident_type": row.get("type"),
                    "preview": row["text"],
                },
            )
        )
    return items


def conversations_for(actor: Any) -> list[dict[str, Any]]:
    """Every conversation on the actor's jobs, newest first, each with
    ``conversation_key``, ``at`` (ISO) and ``unread``."""
    from fikisha.jobs import job_authz

    user = _user(actor)
    if user is None or job_authz.is_admin(actor):
        return []

    # Read-only: the memo only saves repeating the same membership lookup
    # for every job; each module still applies its own party check per job.
    with authz_memo():
        jobs = job_authz.recent_jobs_visible_to(actor, MAX_JOBS)
        items = _items_for_jobs(actor, jobs)

    markers = dict(
        InboxReadMarker.objects.filter(
            user=user, conversation_key__in=[i.key for i in items]
        ).values_list("conversation_key", "last_read_at")
    )
    items.sort(key=lambda i: (-i.at.timestamp(), i.key))

    out: list[dict[str, Any]] = []
    for item in items:
        read_at = markers.get(item.key)
        unread = not item.by_viewer and (read_at is None or item.at > read_at)
        out.append(
            {
                "conversation_key": item.key,
                "at": item.at.isoformat(),
                "unread": unread,
                **item.payload,
            }
        )
    return out


def _position(item: dict[str, Any]) -> tuple[float, str]:
    """Sort position in the newest-first list (time descending, then key)."""
    return (-datetime.fromisoformat(item["at"]).timestamp(), item["conversation_key"])


def _encode_cursor(item: dict[str, Any]) -> str:
    raw = json.dumps([item["at"], item["conversation_key"]]).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_cursor(cursor: str) -> tuple[str, str]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        at, key = json.loads(base64.urlsafe_b64decode(padded.encode()))
        datetime.fromisoformat(at)
        if not isinstance(key, str):
            raise ValueError
        return at, key
    except (ValueError, TypeError, binascii.Error, json.JSONDecodeError) as exc:
        raise InvalidCursor() from exc


def page(
    items: list[dict[str, Any]], *, cursor: str | None, limit: int | None
) -> tuple[list[dict[str, Any]], str | None]:
    """Forward-only cursor paging over the newest-first list. The cursor is
    the position of the last item returned (its time and key), so a page
    stays stable when older items are added below it."""
    size = max(1, min(limit or PAGE_SIZE, MAX_PAGE_SIZE))
    start = 0
    if cursor:
        at, key = _decode_cursor(cursor)
        after = _position({"at": at, "conversation_key": key})
        start = next((n for n, item in enumerate(items) if _position(item) > after), len(items))
    chunk = items[start : start + size]
    has_more = start + size < len(items)
    return chunk, (_encode_cursor(chunk[-1]) if has_more and chunk else None)


def mark_read(*, actor: Any, conversation_key: str) -> None:
    """The person has read this conversation up to now. Only ever touches
    the caller's own marker; a key they can't see simply never matches an
    item of theirs, so nothing is revealed either way."""
    user = _user(actor)
    if user is None:
        raise InvalidConversationKey()
    key = (conversation_key or "").strip().lower()
    if not _KEY.match(key):
        raise InvalidConversationKey()
    InboxReadMarker.objects.update_or_create(
        user=user, conversation_key=key, defaults={"last_read_at": timezone.now()}
    )
