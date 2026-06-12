from rest_framework import serializers

from core.api import AUDIT_FIELDS
from marketing.models import (
    Campaign,
    CampaignRecipient,
    Journey,
    JourneyStep,
    LoyaltyProgram,
    LoyaltyTransaction,
    Promotion,
    Referral,
    ReferralProgram,
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


class ReferralProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferralProgram
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class ReferralSerializer(serializers.ModelSerializer):
    class Meta:
        model = Referral
        fields = "__all__"
        read_only_fields = (
            *AUDIT_FIELDS,
            "code",
            "status",
            "qualified_at",
            "rewarded_at",
            "rejection_reason",
            "referee",
        )


class ReferralQualifySerializer(serializers.Serializer):
    referee = serializers.UUIDField()


class JourneyStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = JourneyStep
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class JourneySerializer(serializers.ModelSerializer):
    steps = JourneyStepSerializer(many=True, read_only=True)

    class Meta:
        model = Journey
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS
