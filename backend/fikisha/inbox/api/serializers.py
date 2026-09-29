from __future__ import annotations

from rest_framework import serializers


class MarkReadSerializer(serializers.Serializer):
    conversation_key = serializers.CharField(max_length=64)
