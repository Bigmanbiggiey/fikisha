"""Ratings enums (trust-and-disputes plan A4, FR-R-1..R-2)."""

from __future__ import annotations

from django.db import models


class RatingSide(models.TextChoices):
    BUSINESS_RATES_OPERATOR = "BUSINESS_RATES_OPERATOR", "Business rates the operator"
    OPERATOR_RATES_BUSINESS = "OPERATOR_RATES_BUSINESS", "Operator rates the business"


#: Who submitted for the side: the business; the solo operator; on a group
#: job the assigned driver or the group manager (first to submit, TE-10).
class RaterParty(models.TextChoices):
    BUSINESS = "BUSINESS", "Business"
    OPERATOR = "OPERATOR", "Operator"
    DRIVER = "DRIVER", "Driver"
    GROUP = "GROUP", "Group manager"


class SubjectKind(models.TextChoices):
    DRIVER = "DRIVER", "Driver"
    GROUP = "GROUP", "Group"
    BUSINESS = "BUSINESS", "Business"


MIN_SCORE = 1
MAX_SCORE = 5
COMMENT_MAX_LENGTH = 1000
