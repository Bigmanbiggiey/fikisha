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
        assert data["commission"]["rate"] == 0.10
        assert data["commission"]["min_fee_kes"] == 4000
        assert data["commission"]["cap_kes"] == 500000
        assert config.current_version() == 1
        assert PlatformConfigVersion.objects.get(version=1).rationale.startswith("Initial default")

    def test_dotted_get(self) -> None:
        config.current()
        assert config.get("commission.model") == "FLAT_WITH_MIN_CAP"
        assert config.get("locales.supported") == ["en", "sw"]
        assert config.get("does.not.exist", "fallback") == "fallback"


class TestApplyChange:
    def test_change_bumps_version_audits_and_emits(self, platform_admin: object) -> None:
        config.current()
        audit_before = AuditLogEntry.objects.count()
        outbox_before = OutboxEvent.objects.count()

        version = config.apply_change(
            patch={"commission": {"rate": 0.08}},
            changed_by=platform_admin,
            rationale="pilot week 5: step commission to 8%",
        )

        assert version.version == 2
        assert config.get("commission.rate") == 0.08
        assert config.get("commission.min_fee_kes") == 4000  # deep-merge preserved siblings
        assert AuditLogEntry.objects.count() == audit_before + 1
        assert OutboxEvent.objects.filter(event_type="platform_config.changed").count() == 1
        assert OutboxEvent.objects.count() == outbox_before + 1

    def test_change_is_not_retroactive(self, platform_admin: object) -> None:
        config.current()
        config.apply_change(
            patch={"commission": {"rate": 0.08}}, changed_by=platform_admin, rationale="x"
        )
        v1 = PlatformConfigVersion.objects.get(version=1)
        assert v1.snapshot["commission"]["rate"] == 0.10  # historical snapshot unchanged

    def test_rationale_required(self, platform_admin: object) -> None:
        config.current()
        with pytest.raises(ValueError):
            config.apply_change(
                patch={"commission": {"rate": 0.05}}, changed_by=platform_admin, rationale="  "
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
                patch={"commission": {"min_fee_kes": -1}},
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
