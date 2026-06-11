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
    Employee,
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
