from __future__ import annotations

from rest_framework import serializers

from fikisha.trust.constants import STORED_TIERS


class SetTierSerializer(serializers.Serializer):
    level = serializers.ChoiceField(choices=[str(t) for t in STORED_TIERS])
    reason = serializers.CharField(max_length=2000)


class DecideProposalSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["CONFIRM", "REJECT"])
    reason = serializers.CharField(max_length=2000)
