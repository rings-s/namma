<<<<<<< HEAD
from django.shortcuts import render

# Create your views here.
=======
from core.api import TenantScopedReadOnlyViewSet, TenantScopedViewSet
from marketing import serializers
from marketing.models import (
    Campaign,
    CampaignRecipient,
    LoyaltyProgram,
    LoyaltyTransaction,
    Promotion,
)


class CampaignViewSet(TenantScopedViewSet):
    queryset = Campaign.objects.all()
    serializer_class = serializers.CampaignSerializer
    search_fields = ["name", "subject"]
    ordering_fields = ["scheduled_at", "created_at"]


class CampaignRecipientViewSet(TenantScopedReadOnlyViewSet):
    # Populated by the campaign dispatch worker.
    queryset = CampaignRecipient.objects.select_related("campaign", "customer")
    serializer_class = serializers.CampaignRecipientSerializer
    org_field = "campaign__organization"


class PromotionViewSet(TenantScopedViewSet):
    queryset = Promotion.objects.all()
    serializer_class = serializers.PromotionSerializer
    search_fields = ["name", "code"]


class LoyaltyProgramViewSet(TenantScopedViewSet):
    queryset = LoyaltyProgram.objects.all()
    serializer_class = serializers.LoyaltyProgramSerializer


class LoyaltyTransactionViewSet(TenantScopedReadOnlyViewSet):
    # Earn/redeem entries are written by the sales pipeline.
    queryset = LoyaltyTransaction.objects.select_related("loyalty_program", "customer", "sale")
    serializer_class = serializers.LoyaltyTransactionSerializer
    org_field = "loyalty_program__organization"
>>>>>>> a3235b4 (feat(db): initialize core relational schema)
