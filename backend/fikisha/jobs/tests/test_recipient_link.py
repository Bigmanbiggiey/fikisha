"""Recipient access-link token security + the Founder Gate amendment
(plain UNIQUE(job_id), no now() in a partial index; request-time checks;
atomic revoke-then-replace under the job lock) — recipient-access.md, plan §11."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from typing import Any

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from fikisha.jobs import recipient as recipient_service
from fikisha.jobs.errors import (
    RecipientActionNotAllowed,
    RecipientLinkInactive,
    RecipientLinkNotFound,
)
from fikisha.jobs.models import RecipientAccessLink

pytestmark = pytest.mark.django_db


@pytest.fixture
def at_destination_job(make_assigned_job: Callable, driver_actor: Any) -> tuple[Any, str]:
    """Drives a job through to AT_DESTINATION, which issues the recipient link.
    Returns ``(job, raw_token)`` — the dev-exposed token from the arrival
    transition (test settings only), the only place it is ever in plaintext."""
    from fikisha.jobs import custody

    job = make_assigned_job()
    custody.arrive_at_pickup(actor=driver_actor, job_id=job.id)
    custody.confirm_pickup_with_otp(actor=driver_actor, job_id=job.id, code="000000")
    custody.start_transit(actor=driver_actor, job_id=job.id)
    out = custody.arrive_at_destination(actor=driver_actor, job_id=job.id)
    job.refresh_from_db()
    return job, out["recipient_link_token"]


@pytest.fixture
def link_and_token(at_destination_job: tuple[Any, str]) -> tuple[RecipientAccessLink, str]:
    job, token = at_destination_job
    return RecipientAccessLink.objects.get(job=job), token


# ─── token model ───────────────────────────────────────────────────
def test_token_is_never_stored_in_plaintext(link_and_token: tuple[Any, str]) -> None:
    link, token = link_and_token
    assert link.token_hash != token
    assert bytes(link.token_lookup) != token.encode()
    assert len(token) >= 40  # 32 bytes urlsafe-b64 ~= 43 chars


def test_issuance_creates_exactly_one_row_per_job(at_destination_job: tuple[Any, str]) -> None:
    job, _token = at_destination_job
    assert RecipientAccessLink.objects.filter(job=job).count() == 1


def test_the_unique_constraint_is_plain_unique_job_id_no_now(
    at_destination_job: tuple[Any, str],
) -> None:
    """The Founder Gate amendment: verify the DB constraint is a plain unique,
    not a time-dependent partial index — a second row for the same job is
    rejected outright by the schema, independent of expiry/revocation."""
    job, _token = at_destination_job
    from django.db import connection

    with connection.cursor() as cur:
        cur.execute(
            "SELECT indexdef FROM pg_indexes WHERE tablename = 'recipient_access_link' "
            "AND indexdef ILIKE '%%job_id%%' AND indexdef ILIKE '%%UNIQUE%%'"
        )
        rows = [r[0] for r in cur.fetchall()]
    assert rows, "expected a unique index on recipient_access_link.job_id"
    assert not any("now(" in r.lower() for r in rows)
    assert not any(" where " in r.lower() for r in rows)  # no partial predicate at all

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            RecipientAccessLink.objects.create(
                job=job,
                token_hash="x",
                token_lookup=b"y" * 32,
                allowed_actions=["VIEW"],
                expires_at=timezone.now() + timedelta(days=1),
            )


# ─── request-time resolution (the amendment's exact check order) ────
def test_valid_unexpired_link_resolves(link_and_token: tuple[Any, str]) -> None:
    link, token = link_and_token
    principal = recipient_service.resolve_recipient(token)
    assert principal.job_id == str(link.job_id)
    assert set(principal.allowed_actions) == {"VIEW", "CONFIRM_RECEIPT", "REPORT_ISSUE"}


def test_expired_link_is_refused(link_and_token: tuple[Any, str]) -> None:
    link, token = link_and_token
    link.expires_at = timezone.now() - timedelta(seconds=1)
    link.save(update_fields=["expires_at"])
    with pytest.raises(RecipientLinkInactive):
        recipient_service.resolve_recipient(token)


def test_revoked_link_is_refused(link_and_token: tuple[Any, str]) -> None:
    link, token = link_and_token
    link.revoked_at = timezone.now()
    link.revoke_reason = "admin"
    link.save(update_fields=["revoked_at", "revoke_reason"])
    with pytest.raises(RecipientLinkInactive):
        recipient_service.resolve_recipient(token)


def test_unknown_token_is_not_found(db: Any) -> None:
    with pytest.raises(RecipientLinkNotFound):
        recipient_service.resolve_recipient("not-a-real-token-at-all")


def test_a_tampered_token_is_not_found(link_and_token: tuple[Any, str]) -> None:
    _link, token = link_and_token
    tampered = token[:-1] + ("a" if token[-1] != "a" else "b")
    with pytest.raises((RecipientLinkNotFound, RecipientLinkInactive)):
        recipient_service.resolve_recipient(tampered)


# ─── replacement (revoke-then-delete under the job lock) ────────────
def test_replacement_after_expiry(at_destination_job: tuple[Any, str]) -> None:
    job, _token = at_destination_job
    old_link = RecipientAccessLink.objects.get(job=job)
    old_link.expires_at = timezone.now() - timedelta(seconds=1)
    old_link.save(update_fields=["expires_at"])

    _new_link, new_token = recipient_service.reissue_link(job_id=job.id)
    assert not RecipientAccessLink.objects.filter(id=old_link.id).exists()  # deleted
    assert RecipientAccessLink.objects.filter(job=job).count() == 1
    principal = recipient_service.resolve_recipient(new_token)
    assert principal.job_id == str(job.id)


def test_replacement_after_explicit_revocation(at_destination_job: tuple[Any, str]) -> None:
    job, _token = at_destination_job
    old_link = RecipientAccessLink.objects.get(job=job)
    new_link, _new_token = recipient_service.reissue_link(job_id=job.id)
    assert new_link.id != old_link.id
    assert not RecipientAccessLink.objects.filter(id=old_link.id).exists()
    assert RecipientAccessLink.objects.filter(job=job).count() == 1


def test_the_old_token_stops_working_after_replacement(at_destination_job: tuple[Any, str]) -> None:
    job, _token = at_destination_job
    _old_link, old_token = recipient_service.reissue_link(job_id=job.id)
    recipient_service.reissue_link(job_id=job.id)
    with pytest.raises(RecipientLinkNotFound):
        recipient_service.resolve_recipient(old_token)  # the row is gone


@pytest.mark.django_db(transaction=True)
def test_concurrent_replacement_serialises_to_one_live_link(
    make_assigned_job: Callable, driver_actor: Any
) -> None:
    """Real concurrent reissues via threads (needs a transactional test DB so
    each thread's own connection can see committed rows and block on the job
    lock). No IntegrityError; exactly one link survives."""
    import threading

    from django.db import connection

    from fikisha.jobs import custody

    job = make_assigned_job()
    custody.arrive_at_pickup(actor=driver_actor, job_id=job.id)
    custody.confirm_pickup_with_otp(actor=driver_actor, job_id=job.id, code="000000")
    custody.start_transit(actor=driver_actor, job_id=job.id)
    custody.arrive_at_destination(actor=driver_actor, job_id=job.id)
    job.refresh_from_db()

    errors: list[BaseException] = []
    tokens: list[str] = []
    lock = threading.Lock()

    def _reissue() -> None:
        try:
            _link, token = recipient_service.reissue_link(job_id=job.id)
            with lock:
                tokens.append(token)
        except BaseException as exc:
            with lock:
                errors.append(exc)
        finally:
            connection.close()  # each thread must not share the main connection

    threads = [threading.Thread(target=_reissue) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, errors
    assert RecipientAccessLink.objects.filter(job=job).count() == 1
    live = [tok for tok in tokens if _resolves(tok)]
    assert len(live) == 1  # only the last writer's token still resolves


def _resolves(token: str) -> bool:
    try:
        recipient_service.resolve_recipient(token)
        return True
    except Exception:
        return False


# ─── capability ceiling ───────────────────────────────────────────
def test_action_outside_allowed_actions_is_denied(db: Any) -> None:
    import uuid

    from fikisha.jobs.recipient import RecipientPrincipal, _require

    narrow = RecipientPrincipal(
        link_id=str(uuid.uuid4()), job_id=str(uuid.uuid4()), allowed_actions=("VIEW",)
    )
    _require(narrow, "VIEW")  # ok
    with pytest.raises(RecipientActionNotAllowed):
        _require(narrow, "CONFIRM_RECEIPT")
