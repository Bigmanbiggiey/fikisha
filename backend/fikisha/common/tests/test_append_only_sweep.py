"""A generic sweep across every append-only model in the app registry.

Every table listed in CLAUDE.md §4 ("Append-only where specified") relies on
*three* independent layers: the model's own ``save()``/``delete()`` guard (per-
instance mutation), the DB ``BEFORE UPDATE/DELETE`` trigger, and
``AppendOnlyQuerySet`` (bulk ``.update()``/``.delete()``). The first two are
exercised per-table by each app's own tests; this sweep instead walks the
Django app registry itself and proves the *third* layer is wired on every
concrete ``AppendOnlyModel`` subclass that exists today — so a future new
append-only table that forgets ``objects = AppendOnlyQuerySet.as_manager()``
fails this test immediately (a real gap here would let a caller bypass the
append-only invariant via ``Model.objects.filter(...).update(...)``, invisible
to per-table tests that only ever exercise the instance-level guard) instead
of relying on someone remembering to check it by hand next time. Phase 2D
Step 12 (invariant/property tests)."""

from __future__ import annotations

import pytest
from django.apps import apps

from fikisha.common.models import AppendOnlyModel, AppendOnlyModelError

pytestmark = pytest.mark.django_db


def _append_only_models() -> list[type]:
    return sorted(
        (m for m in apps.get_models() if issubclass(m, AppendOnlyModel) and not m._meta.abstract),
        key=lambda m: m.__name__,
    )


def test_the_sweep_itself_finds_every_known_table() -> None:
    # A floor, not a ceiling: if this ever shrinks, the sweep below silently
    # stopped covering a table (e.g. an app not installed under this settings
    # module) as loudly as a missing wire-up would.
    names = {m.__name__ for m in _append_only_models()}
    assert names >= {
        "AuditLogEntry",
        "EvidenceAccessLog",
        "IncidentEvidence",
        "IncidentStatement",
        "Resolution",
        "Escalation",
        "Agreement",
        "CancellationRecord",
        "FailureRecord",
        "JobEvent",
        "ProofOfPickup",
        "ProofOfDelivery",
        "RecipientReportedIssue",
        "HighValueApproval",
        "CommissionRecord",
        "CommissionAdjustment",
        "NegotiationEntry",
        "PlatformConfigVersion",
        "VerificationDecision",
    }


@pytest.mark.parametrize("model", _append_only_models(), ids=lambda m: m.__name__)
def test_bulk_update_is_blocked(model: type) -> None:
    with pytest.raises(AppendOnlyModelError):
        model.objects.none().update()


@pytest.mark.parametrize("model", _append_only_models(), ids=lambda m: m.__name__)
def test_bulk_delete_is_blocked(model: type) -> None:
    with pytest.raises(AppendOnlyModelError):
        model.objects.none().delete()
