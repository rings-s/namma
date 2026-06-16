from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from accounts.models import UserRole
from core.api import (
    TenantScopedReadOnlyViewSet,
    TenantScopedViewSet,
    require_org_role,
)
from core.audit import record_audit
from operations import serializers
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
from operations.services import (
    book_appointment,
    employee_loaded_cost,
    organization_labor_summary,
    release_event_capacity,
    reschedule_appointment,
    reserve_event_capacity,
)


class EmployeeViewSet(TenantScopedViewSet):
    queryset = Employee.objects.select_related("user", "branch")
    serializer_class = serializers.EmployeeSerializer
    search_fields = ["employee_code", "job_title", "user__email"]

    @action(detail=True, methods=["get"], url_path="loaded-cost")
    def loaded_cost(self, request, pk=None):
        """Fully loaded monthly cost (salary + GOSI + Qiwa + insurance +
        allowances). Manager+ — this is payroll-sensitive data."""
        employee = self.get_object()
        require_org_role(request.user, employee.organization_id, UserRole.Role.MANAGER)
        cost = employee_loaded_cost(employee)
        return Response(
            {
                "total_monthly": str(cost["total_monthly"]),
                "components": {
                    key: str(value) for key, value in cost["components"].items()
                },
            }
        )

    @action(detail=False, methods=["get"], url_path="labor-summary")
    def labor_summary(self, request):
        """Org labor compliance snapshot: saudization ratio (Nitaqat input)
        and total loaded payroll cost. Manager+; ?organization=<id>."""
        organization_id = request.query_params.get("organization")
        if not organization_id:
            org_ids = self.allowed_organization_ids()
            if org_ids is None or len(org_ids) != 1:
                return Response({"detail": "Pass ?organization=<id>."}, status=400)
            organization_id = org_ids[0]
        require_org_role(request.user, organization_id, UserRole.Role.MANAGER)
        summary = organization_labor_summary(organization_id)
        summary["total_loaded_monthly_cost"] = str(summary["total_loaded_monthly_cost"])
        return Response(summary)


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
    queryset = Appointment.objects.select_related(
        "customer", "employee", "service", "branch"
    )
    serializer_class = serializers.AppointmentSerializer
    search_fields = ["customer__first_name", "customer__last_name", "customer__phone"]
    ordering_fields = ["scheduled_at", "created_at"]

    def perform_create(self, serializer):
        """Create the appointment, rejecting a double-booking of the assigned
        employee under concurrency (the slot check holds a row lock)."""
        self._check_tenant_ownership(serializer)
        try:
            appointment = book_appointment(serializer)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)
        record_audit(
            action="booking.appointment_created",
            entity_type="Appointment",
            entity_id=appointment.id,
            organization=appointment.organization,
            user=self.request.user,
            new_values={
                "scheduled_at": appointment.scheduled_at.isoformat(),
                "employee": str(appointment.employee_id),
            },
            request=self.request,
        )

    def perform_update(self, serializer):
        """Reschedule, re-validating the employee calendar when the slot or
        assignee changed."""
        self._check_tenant_ownership(serializer)
        try:
            reschedule_appointment(serializer)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)


class AppointmentReminderViewSet(TenantScopedViewSet):
    queryset = AppointmentReminder.objects.select_related("appointment")
    serializer_class = serializers.AppointmentReminderSerializer
    org_field = "appointment__organization"


class BookingViewSet(TenantScopedViewSet):
    queryset = Booking.objects.select_related("customer", "event", "branch")
    serializer_class = serializers.BookingSerializer
    search_fields = ["booking_number"]
    ordering_fields = ["booked_at", "created_at"]

    #: Booking statuses that no longer hold a reserved seat.
    _RELEASED_STATUSES = (Booking.Status.CANCELLED, Booking.Status.NO_SHOW)

    def perform_create(self, serializer):
        """Create the booking; for event bookings reserve capacity atomically
        so concurrent requests cannot oversell the event. The booking number is
        allocated server-side from DocumentSequence."""
        self._check_tenant_ownership(serializer)
        from django.db import transaction

        from financials.models import DocumentSequence
        from financials.services import next_document_number

        data = serializer.validated_data
        event = data.get("event")
        quantity = data.get("quantity", 1)
        try:
            with transaction.atomic():
                if event is not None:
                    reserve_event_capacity(event.id, quantity)
                booking = serializer.save(
                    booking_number=next_document_number(
                        organization=data["organization"],
                        document_type=DocumentSequence.DocumentType.BOOKING,
                        branch=data.get("branch"),
                    )
                )
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages)
        record_audit(
            action="booking.booking_created",
            entity_type="Booking",
            entity_id=booking.id,
            organization=booking.organization,
            user=self.request.user,
            new_values={
                "booking_number": booking.booking_number,
                "event": str(booking.event_id),
                "quantity": booking.quantity,
            },
            request=self.request,
        )

    def perform_update(self, serializer):
        """On a transition into a cancelled/no-show state, return the reserved
        seats to the event."""
        self._check_tenant_ownership(serializer)
        from django.db import transaction

        instance = serializer.instance
        was_active = instance.status not in self._RELEASED_STATUSES
        new_status = serializer.validated_data.get("status", instance.status)
        with transaction.atomic():
            booking = serializer.save()
            if (
                was_active
                and new_status in self._RELEASED_STATUSES
                and booking.event_id is not None
            ):
                release_event_capacity(booking.event_id, booking.quantity)


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
    queryset = CommissionEntry.objects.select_related(
        "employee", "payroll_period", "sale"
    )
    serializer_class = serializers.CommissionEntrySerializer
    ordering_fields = ["created_at"]


class CommissionRuleViewSet(TenantScopedViewSet):
    queryset = CommissionRule.objects.select_related(
        "branch", "employee", "service", "product"
    )
    serializer_class = serializers.CommissionRuleSerializer
    search_fields = ["name"]


class EmployeeCostComponentViewSet(TenantScopedViewSet):
    queryset = EmployeeCostComponent.objects.select_related("employee")
    serializer_class = serializers.EmployeeCostComponentSerializer
    ordering_fields = ["effective_from", "created_at"]


class WaitlistEntryViewSet(TenantScopedViewSet):
    queryset = WaitlistEntry.objects.select_related(
        "branch", "customer", "service", "preferred_employee"
    )
    serializer_class = serializers.WaitlistEntrySerializer
    ordering_fields = ["priority", "created_at"]
