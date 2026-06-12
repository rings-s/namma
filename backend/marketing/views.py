from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from accounts.models import UserRole
from core.api import TenantScopedReadOnlyViewSet, TenantScopedViewSet, require_org_role
from marketing import serializers
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
from marketing.services import (
    create_referral,
    qualify_referral,
    validate_campaign_sendable,
)
from marketing.tasks import send_campaign_task


class CampaignViewSet(TenantScopedViewSet):
    queryset = Campaign.objects.all()
    serializer_class = serializers.CampaignSerializer
    search_fields = ["name", "subject"]
    ordering_fields = ["scheduled_at", "created_at"]

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        """Queue a campaign fan-out to its consented audience. Marketer+."""
        campaign = self.get_object()
        require_org_role(request.user, campaign.organization_id, UserRole.Role.MARKETER)
        try:
            validate_campaign_sendable(campaign)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)
        send_campaign_task.delay(str(campaign.pk))
        campaign.refresh_from_db()
        return Response(
            serializers.CampaignSerializer(campaign).data,
            status=status.HTTP_202_ACCEPTED,
        )


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
    queryset = LoyaltyTransaction.objects.select_related(
        "loyalty_program", "customer", "sale"
    )
    serializer_class = serializers.LoyaltyTransactionSerializer
    org_field = "loyalty_program__organization"


class ReferralProgramViewSet(TenantScopedViewSet):
    queryset = ReferralProgram.objects.all()
    serializer_class = serializers.ReferralProgramSerializer


class ReferralViewSet(TenantScopedViewSet):
    """Referral lifecycle. Creation mints the code (service-side cap
    checks); qualification runs the fraud guards and pays the rewards."""

    queryset = Referral.objects.select_related("program", "referrer", "referee")
    serializer_class = serializers.ReferralSerializer
    http_method_names = ["get", "post", "head", "options"]
    search_fields = ["code"]

    def perform_create(self, serializer):
        self._check_tenant_ownership(serializer)
        try:
            referral = create_referral(
                serializer.validated_data["program"],
                serializer.validated_data["referrer"],
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)
        serializer.instance = referral

    @action(detail=True, methods=["post"])
    def qualify(self, request, pk=None):
        """Attach a referee and settle the referral (reward or reject)."""
        referral = self.get_object()
        require_org_role(
            request.user, referral.organization_id, UserRole.Role.RECEPTIONIST
        )
        params = serializers.ReferralQualifySerializer(data=request.data)
        params.is_valid(raise_exception=True)
        from customers.models import Customer

        referee = Customer.objects.filter(
            pk=params.validated_data["referee"],
            organization_id=referral.organization_id,
        ).first()
        if referee is None:
            raise ValidationError("Unknown referee.")
        try:
            referral = qualify_referral(referral, referee)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)
        return Response(self.get_serializer(referral).data)


class JourneyViewSet(TenantScopedViewSet):
    queryset = Journey.objects.prefetch_related("steps")
    serializer_class = serializers.JourneySerializer


class JourneyStepViewSet(TenantScopedViewSet):
    queryset = JourneyStep.objects.select_related("journey", "template")
    serializer_class = serializers.JourneyStepSerializer
    org_field = "journey__organization"
