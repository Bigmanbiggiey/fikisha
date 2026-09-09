from __future__ import annotations

from django.conf import settings
from django.db import models

from fikisha.common.models import AppendOnlyModel, AppendOnlyQuerySet, TimestampedModel


class Zone(TimestampedModel):
    """A named geographic operating area (Phase 1 domain-architecture: zones are
    part of Platform Configuration; ``config.zones``).

    Phase 2B seeds a single ``KITENGELA`` zone — the founder's zone breakdown is
    deferred (D-PIL-5), so the pilot area is one zone until it is supplied.
    Admin-extensible; polygon geometry is a later concern (no GIS in 2B).
    """

    code = models.CharField(max_length=40, unique=True)
    name_en = models.CharField(max_length=120)
    name_sw = models.CharField(max_length=120)
    active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "config_zone"
        ordering = ["sort_order", "code"]

    def __str__(self) -> str:
        return self.code


class PlatformConfigVersion(AppendOnlyModel):
    """An immutable snapshot of the whole config at a point in time."""

    version = models.PositiveIntegerField(unique=True, editable=False)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="config_versions",
    )
    rationale = models.TextField()
    snapshot = models.JSONField()

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        db_table = "platform_config_version"
        ordering = ["-version"]

    def __str__(self) -> str:
        return f"PlatformConfigVersion v{self.version}"


class PlatformConfig(models.Model):
    """The single live configuration row (pk fixed at 1)."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    data = models.JSONField()
    current_version = models.ForeignKey(
        PlatformConfigVersion, null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "platform_config"
        constraints = [
            models.CheckConstraint(condition=models.Q(id=1), name="platform_config_singleton")
        ]

    def __str__(self) -> str:
        version_obj = self.current_version if self.current_version_id else None
        v = version_obj.version if version_obj is not None else "unversioned"
        return f"PlatformConfig (v{v})"
