from __future__ import annotations

from typing import Any

from rest_framework import serializers


class SubmitRatingSerializer(serializers.Serializer[dict[str, Any]]):
    score = serializers.IntegerField()
    comment = serializers.CharField(max_length=4000, required=False, allow_blank=True, default="")
