from rest_framework import serializers

from core.api import AUDIT_FIELDS
from marketing.models import (
    Campaign,
    CampaignRecipient,
    LoyaltyProgram,
    LoyaltyTransaction,
    Promotion,
)


class CampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campaign
        fields = "__all__"
        read_only_fields = (*AUDIT_FIELDS, "sent_at")


class CampaignRecipientSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignRecipient
        fields = "__all__"


class PromotionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promotion
        fields = "__all__"
        read_only_fields = (*AUDIT_FIELDS, "used_count")


class LoyaltyProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoyaltyProgram
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class LoyaltyTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoyaltyTransaction
        fields = "__all__"
