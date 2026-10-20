"""Ratings (trust-and-disputes plan A4, FR-R-1, FR-O-8).

One rating per completed job per side, append-only. A business's rating of
the operator side records both the assigned driver and, when the job was
the group's, the group (FR-O-8: it attaches to both); each average groups by
one subject, so no rating is counted twice in any average. The operator
side's rating is about the business. Subjects come from the job's
assignment, never from the client.

Comments are staff-only (TE-3).
"""

from __future__ import annotations

from django.conf import settings
from django.db import models

from fikisha.common.models import AppendOnlyModel, AppendOnlyQuerySet
from fikisha.ratings.constants import MAX_SCORE, MIN_SCORE, RaterParty, RatingSide


class Rating(AppendOnlyModel):
    job = models.ForeignKey("jobs.Job", on_delete=models.PROTECT, related_name="ratings")
    side = models.CharField(max_length=24, choices=RatingSide.choices)
    score = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True, default="")
    rater = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    rater_party = models.CharField(max_length=10, choices=RaterParty.choices)
    driver_profile = models.ForeignKey(
        "operators.OperatorProfile",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    group = models.ForeignKey(
        "groups.OperatorGroup", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    business = models.ForeignKey(
        "business.BusinessAccount",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        db_table = "rating"
        constraints = [
            models.UniqueConstraint(fields=["job", "side"], name="uq_rating_one_per_side"),
            models.CheckConstraint(
                condition=models.Q(score__gte=MIN_SCORE, score__lte=MAX_SCORE),
                name="ck_rating_score_range",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(side=RatingSide.BUSINESS_RATES_OPERATOR, driver_profile__isnull=False)
                    | models.Q(side=RatingSide.OPERATOR_RATES_BUSINESS, business__isnull=False)
                ),
                name="ck_rating_subject_for_side",
            ),
        ]
        indexes = [
            models.Index(fields=["driver_profile", "created_at"], name="ix_rating_driver"),
            models.Index(fields=["group", "created_at"], name="ix_rating_group"),
            models.Index(fields=["business", "created_at"], name="ix_rating_business"),
        ]
