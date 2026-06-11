from rest_framework import serializers

from ai.models import AIConversation, AIMessage, AIRecommendation
from core.api import AUDIT_FIELDS


class AIConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIConversation
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class AIMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIMessage
        fields = "__all__"
        read_only_fields = (*AUDIT_FIELDS, "tokens_used")


class AIRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIRecommendation
        fields = "__all__"
        read_only_fields = (*AUDIT_FIELDS, "type", "title", "description", "priority", "data")
