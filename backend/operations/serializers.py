from rest_framework import serializers

from core.api import AUDIT_FIELDS
from operations.models import (
    Appointment,
    AppointmentReminder,
    Booking,
    BookingAttendee,
    BookingDeposit,
    CancellationPolicy,
    CommissionEntry,
    CommissionRule,
    Employee,
    EmployeeCostComponent,
    EmployeeSchedule,
    EmployeeService,
    EmployeeShift,
    Event,
    PayrollPeriod,
    QueueTicket,
    RecurrenceRule,
    Resource,
    ResourceSchedule,
    SlotHold,
    Ticket,
    TicketType,
    TicketVerification,
    WaitlistEntry,
)


class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class EmployeeScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeSchedule
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class EmployeeServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeService
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class EmployeeShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeShift
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class RecurrenceRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecurrenceRule
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = "__all__"
        read_only_fields = (*AUDIT_FIELDS, "booked_count")


class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = "__all__"
        read_only_fields = (*AUDIT_FIELDS, "version")


class AppointmentReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppointmentReminder
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = "__all__"
        read_only_fields = (*AUDIT_FIELDS, "version")


class BookingAttendeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingAttendee
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class BookingDepositSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingDeposit
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class TicketTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketType
        fields = "__all__"
        read_only_fields = (*AUDIT_FIELDS, "quantity_sold")


class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = "__all__"
        read_only_fields = (*AUDIT_FIELDS, "used_count")


class TicketVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketVerification
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class ResourceScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceSchedule
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class SlotHoldSerializer(serializers.ModelSerializer):
    class Meta:
        model = SlotHold
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class CancellationPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = CancellationPolicy
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class QueueTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = QueueTicket
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class PayrollPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollPeriod
        fields = "__all__"
        read_only_fields = (*AUDIT_FIELDS, "locked_at", "locked_by")


class CommissionEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = CommissionEntry
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class CommissionRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommissionRule
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS

    def validate(self, attrs):
        basis = attrs.get("basis", getattr(self.instance, "basis", None))
        if basis == CommissionRule.Basis.PERCENT and not attrs.get(
            "rate_percent", getattr(self.instance, "rate_percent", None)
        ):
            raise serializers.ValidationError(
                {"rate_percent": "Percentage rules need a rate."}
            )
        if basis == CommissionRule.Basis.FIXED and not attrs.get(
            "fixed_amount", getattr(self.instance, "fixed_amount", None)
        ):
            raise serializers.ValidationError(
                {"fixed_amount": "Fixed rules need an amount."}
            )
        if basis == CommissionRule.Basis.TIERED and not attrs.get(
            "tiers", getattr(self.instance, "tiers", None)
        ):
            raise serializers.ValidationError({"tiers": "Tiered rules need tiers."})
        if attrs.get("service") is not None and attrs.get("product") is not None:
            raise serializers.ValidationError(
                "A rule targets a service or a product, not both."
            )
        return attrs


class EmployeeCostComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeCostComponent
        fields = "__all__"
        read_only_fields = AUDIT_FIELDS


class WaitlistEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = WaitlistEntry
        fields = "__all__"
        read_only_fields = (*AUDIT_FIELDS, "offered_at", "offer_expires_at")
