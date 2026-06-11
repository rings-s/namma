<<<<<<< HEAD
from django.shortcuts import render

# Create your views here.
=======
from core.api import TenantScopedReadOnlyViewSet, TenantScopedViewSet
from operations import serializers
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


class EmployeeViewSet(TenantScopedViewSet):
    queryset = Employee.objects.select_related("user", "branch")
    serializer_class = serializers.EmployeeSerializer
    search_fields = ["employee_code", "job_title", "user__email"]


class EmployeeScheduleViewSet(TenantScopedViewSet):
    queryset = EmployeeSchedule.objects.select_related("employee")
    serializer_class = serializers.EmployeeScheduleSerializer
    org_field = "employee__organization"


class EmployeeServiceViewSet(TenantScopedViewSet):
    queryset = EmployeeService.objects.select_related("employee", "service")
    serializer_class = serializers.EmployeeServiceSerializer
    org_field = "employee__organization"


class EmployeeShiftViewSet(TenantScopedViewSet):
    queryset = EmployeeShift.objects.select_related("employee", "branch")
    serializer_class = serializers.EmployeeShiftSerializer
    org_field = "employee__organization"
    ordering_fields = ["shift_date"]


class RecurrenceRuleViewSet(TenantScopedViewSet):
    queryset = RecurrenceRule.objects.all()
    serializer_class = serializers.RecurrenceRuleSerializer


class EventViewSet(TenantScopedViewSet):
    queryset = Event.objects.select_related("branch")
    serializer_class = serializers.EventSerializer
    search_fields = ["name"]
    ordering_fields = ["start_datetime", "created_at"]


class AppointmentViewSet(TenantScopedViewSet):
    queryset = Appointment.objects.select_related("customer", "employee", "service", "branch")
    serializer_class = serializers.AppointmentSerializer
    search_fields = ["customer__first_name", "customer__last_name", "customer__phone"]
    ordering_fields = ["scheduled_at", "created_at"]


class AppointmentReminderViewSet(TenantScopedViewSet):
    queryset = AppointmentReminder.objects.select_related("appointment")
    serializer_class = serializers.AppointmentReminderSerializer
    org_field = "appointment__organization"


class BookingViewSet(TenantScopedViewSet):
    queryset = Booking.objects.select_related("customer", "event", "branch")
    serializer_class = serializers.BookingSerializer
    search_fields = ["booking_number"]
    ordering_fields = ["booked_at", "created_at"]


class BookingAttendeeViewSet(TenantScopedViewSet):
    queryset = BookingAttendee.objects.select_related("booking", "customer")
    serializer_class = serializers.BookingAttendeeSerializer
    org_field = "booking__organization"


class BookingDepositViewSet(TenantScopedViewSet):
    queryset = BookingDeposit.objects.select_related("booking", "payment_intent")
    serializer_class = serializers.BookingDepositSerializer


class TicketTypeViewSet(TenantScopedViewSet):
    queryset = TicketType.objects.select_related("event")
    serializer_class = serializers.TicketTypeSerializer


class TicketViewSet(TenantScopedViewSet):
    queryset = Ticket.objects.select_related("customer", "booking", "branch")
    serializer_class = serializers.TicketSerializer
    search_fields = ["ticket_number", "qr_code_data"]


class TicketVerificationViewSet(TenantScopedViewSet):
    queryset = TicketVerification.objects.select_related("ticket", "verified_by")
    serializer_class = serializers.TicketVerificationSerializer
    org_field = "ticket__organization"


class ResourceViewSet(TenantScopedViewSet):
    queryset = Resource.objects.select_related("branch")
    serializer_class = serializers.ResourceSerializer
    search_fields = ["name", "resource_type"]


class ResourceScheduleViewSet(TenantScopedViewSet):
    queryset = ResourceSchedule.objects.select_related("resource")
    serializer_class = serializers.ResourceScheduleSerializer
    org_field = "resource__organization"


class SlotHoldViewSet(TenantScopedViewSet):
    queryset = SlotHold.objects.select_related("employee", "resource", "branch")
    serializer_class = serializers.SlotHoldSerializer


class CancellationPolicyViewSet(TenantScopedViewSet):
    queryset = CancellationPolicy.objects.select_related("branch", "service")
    serializer_class = serializers.CancellationPolicySerializer


class QueueTicketViewSet(TenantScopedViewSet):
    queryset = QueueTicket.objects.select_related("customer", "service", "branch")
    serializer_class = serializers.QueueTicketSerializer
    ordering_fields = ["position", "created_at"]


class PayrollPeriodViewSet(TenantScopedViewSet):
    queryset = PayrollPeriod.objects.all()
    serializer_class = serializers.PayrollPeriodSerializer
    ordering_fields = ["period_start"]


class CommissionEntryViewSet(TenantScopedReadOnlyViewSet):
    # Commission entries are derived from sales; written by the payroll service.
    queryset = CommissionEntry.objects.select_related("employee", "payroll_period", "sale")
    serializer_class = serializers.CommissionEntrySerializer
    ordering_fields = ["created_at"]
>>>>>>> a3235b4 (feat(db): initialize core relational schema)
