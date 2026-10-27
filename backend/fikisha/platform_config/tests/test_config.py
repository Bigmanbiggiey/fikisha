"""Platform configuration foundation tests."""

from __future__ import annotations

import pytest

from fikisha.audit.models import AuditLogEntry
from fikisha.outbox.models import OutboxEvent
from fikisha.platform_config import services as config
from fikisha.platform_config.defaults import ConfigValidationError
from fikisha.platform_config.models import PlatformConfig, PlatformConfigVersion

pytestmark = pytest.mark.django_db


class TestBootstrap:
    def test_first_read_seeds_version_1(self) -> None:
        data = config.current()
        assert data["commission"] == {
            "model": "SPLIT_FLAT",
            "business_rate": 0.05,
            "operator_rate": 0.05,
        }
        assert config.current_version() == 1
        assert PlatformConfigVersion.objects.get(version=1).rationale.startswith("Initial default")

    def test_dotted_get(self) -> None:
        config.current()
        assert config.get("commission.model") == "SPLIT_FLAT"
        assert config.get("locales.supported") == ["en", "sw"]
        assert config.get("does.not.exist", "fallback") == "fallback"


class TestApplyChange:
    def test_change_bumps_version_audits_and_emits(self, platform_admin: object) -> None:
        config.current()
        audit_before = AuditLogEntry.objects.count()
        outbox_before = OutboxEvent.objects.count()

        version = config.apply_change(
            patch={"commission": {"business_rate": 0.04}},
            changed_by=platform_admin,
            rationale="pilot week 5: step the business side to 4%",
        )

        assert version.version == 2
        assert config.get("commission.business_rate") == 0.04
        assert config.get("commission.operator_rate") == 0.05  # deep-merge preserved siblings
        assert AuditLogEntry.objects.count() == audit_before + 1
        assert OutboxEvent.objects.filter(event_type="platform_config.changed").count() == 1
        assert OutboxEvent.objects.count() == outbox_before + 1

    def test_change_is_not_retroactive(self, platform_admin: object) -> None:
        config.current()
        config.apply_change(
            patch={"commission": {"business_rate": 0.08}}, changed_by=platform_admin, rationale="x"
        )
        v1 = PlatformConfigVersion.objects.get(version=1)
        assert v1.snapshot["commission"]["business_rate"] == 0.05  # historical snapshot unchanged

    def test_rationale_required(self, platform_admin: object) -> None:
        config.current()
        with pytest.raises(ValueError):
            config.apply_change(
                patch={"commission": {"business_rate": 0.05}},
                changed_by=platform_admin,
                rationale="  ",
            )

    def test_invalid_change_rejected(self, platform_admin: object) -> None:
        config.current()
        with pytest.raises(ConfigValidationError):
            config.apply_change(
                patch={"commission": {"model": "MADE_UP"}},
                changed_by=platform_admin,
                rationale="should fail",
            )
        with pytest.raises(ConfigValidationError):
            config.apply_change(
                patch={"commission": {"operator_rate": -0.01}},
                changed_by=platform_admin,
                rationale="should fail",
            )
        assert config.current_version() == 1  # nothing applied

    def test_config_version_is_append_only(self) -> None:
        config.current()
        v = PlatformConfigVersion.objects.get(version=1)
        from fikisha.common.models import AppendOnlyModelError

        v.rationale = "tampered"
        with pytest.raises(AppendOnlyModelError):
            v.save()

    def test_platform_config_singleton(self) -> None:
        config.current()
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            PlatformConfig.objects.create(id=2, data={})


class TestReplaceSection:
    """The commission split (ADR-2D-55) replaces the whole ``commission``
    section on a live config, so the old keys really go."""

    _SPLIT = {"model": "SPLIT_FLAT", "business_rate": 0.05, "operator_rate": 0.05}

    def test_no_live_config_does_nothing(self) -> None:
        assert (
            config.replace_section(
                key="commission", value=self._SPLIT, changed_by=None, rationale="x"
            )
            is None
        )
        assert not PlatformConfig.objects.exists()

    def test_the_same_value_does_nothing(self) -> None:
        config.current()
        assert (
            config.replace_section(
                key="commission", value=self._SPLIT, changed_by=None, rationale="x"
            )
            is None
        )
        assert config.current_version() == 1

    def test_an_old_section_is_replaced_whole_versioned_and_audited(self) -> None:
        config.current()
        cfg = PlatformConfig.objects.get(pk=1)
        cfg.data = {
            **cfg.data,
            "commission": {
                "model": "FLAT_WITH_MIN_CAP",
                "rate": 0.10,
                "min_fee_kes": 4000,
                "cap_kes": 500000,
                "party_liable": "OPERATOR",
            },
        }
        cfg.save(update_fields=["data"])
        audit_before = AuditLogEntry.objects.count()

        version = config.replace_section(
            key="commission",
            value=self._SPLIT,
            changed_by=None,
            rationale="commission split",
            source_channel="CLI",
        )

        assert version is not None and version.version == 2
        assert config.current()["commission"] == self._SPLIT
        entry = AuditLogEntry.objects.order_by("-seq").first()
        assert AuditLogEntry.objects.count() == audit_before + 1
        assert entry is not None and entry.action == "platform_config.changed"
        assert entry.source_channel == "CLI"

    def test_leftover_old_keys_are_refused(self, platform_admin: object) -> None:
        config.current()
        with pytest.raises(ConfigValidationError):
            config.apply_change(
                patch={"commission": {"cap_kes": 500000}},
                changed_by=platform_admin,
                rationale="should fail",
            )
