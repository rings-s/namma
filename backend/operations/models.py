"""Operations: staff, scheduling, appointments, bookings, events,
tickets, resources, queueing and payroll."""

from django.db import models

from django.conf import settings
from django.utils import timezone

from core.models import BaseModel, Channel, Weekday


# ---------------------------------------------------------------------------
# Employees
# ---------------------------------------------------------------------------


class Employee(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="employee_profiles",
        null=True,
        blank=True,
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="employees",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.SET_NULL,
        related_name="employees",
        null=True,
        blank=True,
    )
    employee_code = models.CharField(max_length=50, blank=True)
    job_title = models.CharField(max_length=150, blank=True)
    department = models.CharField(max_length=150, blank=True)
    hire_date = models.DateField(null=True, blank=True)
    # Saudi labor compliance: Nitaqat saudization ratios and GOSI brackets
    # both hinge on nationality; the monthly salary anchors loaded-cost math.
    is_saudi = models.BooleanField(default=False)
    monthly_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    hourly_rate = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    is_active = models.BooleanField(default=True)
    services = models.ManyToManyField(
        "commerce.Service",
        through="EmployeeService",
        related_name="employees",
        blank=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["organization", "is_active"]),
        ]

    def __str__(self):
        if self.user:
            return f"{self.user.get_full_name()} ({self.job_title or 'Employee'})"
        return self.employee_code or str(self.id)


class EmployeeSchedule(BaseModel):
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="schedules"
    )
    day_of_week = models.PositiveSmallIntegerField(choices=Weekday.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ["day_of_week", "start_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "day_of_week"],
                name="uniq_employee_schedule_per_day",
            )
        ]

    def __str__(self):
        return f"{self.employee} - {self.get_day_of_week_display()}"


class EmployeeService(BaseModel):
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="employee_services"
    )
    service = models.ForeignKey(
        "commerce.Service",
        on_delete=models.CASCADE,
        related_name="employee_services",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "service"], name="uniq_employee_service"
            )
        ]

    def __str__(self):
        return f"{self.employee} -> {self.service}"


class EmployeeShift(BaseModel):
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="shifts"
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.CASCADE,
        related_name="employee_shifts",
    )
    shift_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["shift_date", "start_time"]
        indexes = [
            models.Index(fields=["branch", "shift_date"]),
            models.Index(fields=["employee", "shift_date"]),
        ]

    def __str__(self):
        return f"{self.employee} @ {self.branch} on {self.shift_date}"


# ---------------------------------------------------------------------------
# Recurrence & events
# ---------------------------------------------------------------------------


class RecurrenceRule(BaseModel):
    class Frequency(models.TextChoices):
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"
        YEARLY = "yearly", "Yearly"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="recurrence_rules",
    )
    frequency = models.CharField(max_length=10, choices=Frequency.choices)
    interval = models.PositiveIntegerField(default=1)
    days_of_week = models.JSONField(default=list, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    occurrence_count = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"Every {self.interval} {self.get_frequency_display().lower()} from {self.start_date}"


class Event(BaseModel):
    class EventType(models.TextChoices):
        CLASS = "class", "Class"
        WORKSHOP = "workshop", "Workshop"
        SESSION = "session", "Session"
        SPECIAL = "special", "Special Event"
        OTHER = "other", "Other"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="events",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.SET_NULL,
        related_name="events",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    event_type = models.CharField(
        max_length=20, choices=EventType.choices, default=EventType.OTHER
    )
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    capacity = models.IntegerField(default=0)
    booked_count = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    location = models.CharField(max_length=255, blank=True)
    image_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["start_datetime"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(capacity__gte=0), name="event_capacity_gte_0"
            )
        ]
        indexes = [
            models.Index(fields=["organization", "start_datetime"]),
        ]

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Appointments
# ---------------------------------------------------------------------------


class Appointment(BaseModel):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        CONFIRMED = "confirmed", "Confirmed"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No Show"

    class Source(models.TextChoices):
        ONLINE = "online", "Online"
        PHONE = "phone", "Phone"
        WALK_IN = "walk_in", "Walk-in"
        STAFF = "staff", "Staff"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="appointments",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.CASCADE,
        related_name="appointments",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="appointments",
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        related_name="appointments",
        null=True,
        blank=True,
    )
    service = models.ForeignKey(
        "commerce.Service",
        on_delete=models.PROTECT,
        related_name="appointments",
    )
    scheduled_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=30)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SCHEDULED
    )
    notes = models.TextField(blank=True)
    source = models.CharField(
        max_length=20, choices=Source.choices, default=Source.STAFF
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["scheduled_at"]
        indexes = [
            models.Index(fields=["organization", "scheduled_at"]),
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["branch", "scheduled_at"]),
            models.Index(fields=["employee", "scheduled_at"]),
        ]

    def __str__(self):
        return f"{self.customer} - {self.service} @ {self.scheduled_at:%Y-%m-%d %H:%M}"


class AppointmentReminder(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    appointment = models.ForeignKey(
        Appointment, on_delete=models.CASCADE, related_name="reminders"
    )
    reminder_type = models.CharField(max_length=20, choices=Channel.choices)
    scheduled_for = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )

    class Meta:
        ordering = ["scheduled_for"]
        indexes = [
            models.Index(fields=["status", "scheduled_for"]),
        ]

    def __str__(self):
        return f"{self.get_reminder_type_display()} reminder for {self.appointment_id}"


# ---------------------------------------------------------------------------
# Bookings
# ---------------------------------------------------------------------------


class Booking(BaseModel):
    class BookingType(models.TextChoices):
        SERVICE = "service", "Service"
        EVENT = "event", "Event"
        CLASS = "class", "Class"
        RESOURCE = "resource", "Resource"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No Show"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    event = models.ForeignKey(
        Event,
        on_delete=models.SET_NULL,
        related_name="bookings",
        null=True,
        blank=True,
    )
    booking_number = models.CharField(max_length=50, unique=True)
    booking_type = models.CharField(
        max_length=20, choices=BookingType.choices, default=BookingType.SERVICE
    )
    quantity = models.PositiveIntegerField(default=1)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    booked_at = models.DateTimeField(default=timezone.now)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    recurrence_rule = models.ForeignKey(
        RecurrenceRule,
        on_delete=models.SET_NULL,
        related_name="bookings",
        null=True,
        blank=True,
    )
    version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["-booked_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "booked_at"]),
            models.Index(fields=["branch", "booked_at"]),
        ]

    def __str__(self):
        return self.booking_number


class BookingAttendee(BaseModel):
    class Status(models.TextChoices):
        REGISTERED = "registered", "Registered"
        CHECKED_IN = "checked_in", "Checked In"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No Show"

    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name="attendees"
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="booking_attendances",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.REGISTERED
    )
    checked_in_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.customer} @ {self.booking}"


class BookingDeposit(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FORFEITED = "forfeited", "Forfeited"
        REFUNDED = "refunded", "Refunded"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="booking_deposits",
    )
    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name="deposits"
    )
    payment_intent = models.ForeignKey(
        "financials.PaymentIntent",
        on_delete=models.SET_NULL,
        related_name="booking_deposits",
        null=True,
        blank=True,
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    forfeited_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Deposit {self.amount} for {self.booking}"


# ---------------------------------------------------------------------------
# Tickets
# ---------------------------------------------------------------------------


class TicketType(BaseModel):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="ticket_types",
    )
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="ticket_types"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity_available = models.PositiveIntegerField(default=0)
    quantity_sold = models.PositiveIntegerField(default=0)
    max_per_booking = models.PositiveIntegerField(default=1)
    valid_duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.event} - {self.name}"


class Ticket(BaseModel):
    class Status(models.TextChoices):
        ISSUED = "issued", "Issued"
        ACTIVE = "active", "Active"
        USED = "used", "Used"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="tickets",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.SET_NULL,
        related_name="tickets",
        null=True,
        blank=True,
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        related_name="tickets",
        null=True,
        blank=True,
    )
    booking = models.ForeignKey(
        Booking,
        on_delete=models.SET_NULL,
        related_name="tickets",
        null=True,
        blank=True,
    )
    ticket_number = models.CharField(max_length=50, unique=True)
    qr_code_data = models.CharField(max_length=255, unique=True)
    qr_code_url = models.URLField(blank=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    max_uses = models.PositiveIntegerField(default=1)
    used_count = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ISSUED
    )
    issued_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
        ]

    def __str__(self):
        return self.ticket_number


class TicketVerification(BaseModel):
    class Method(models.TextChoices):
        QR_SCAN = "qr_scan", "QR Scan"
        MANUAL = "manual", "Manual"
        NFC = "nfc", "NFC"

    class Status(models.TextChoices):
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name="verifications"
    )
    verified_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        related_name="ticket_verifications",
        null=True,
        blank=True,
    )
    verification_method = models.CharField(
        max_length=20, choices=Method.choices, default=Method.QR_SCAN
    )
    status = models.CharField(max_length=20, choices=Status.choices)
    rejection_reason = models.TextField(blank=True)
    device_info = models.CharField(max_length=255, blank=True)
    location_data = models.JSONField(default=dict, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.ticket} - {self.get_status_display()}"


# ---------------------------------------------------------------------------
# Resources, slot holds, policies, queue
# ---------------------------------------------------------------------------


class Resource(BaseModel):
    class ResourceType(models.TextChoices):
        ROOM = "room", "Room"
        EQUIPMENT = "equipment", "Equipment"
        STATION = "station", "Station"
        VEHICLE = "vehicle", "Vehicle"
        OTHER = "other", "Other"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="resources",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.SET_NULL,
        related_name="resources",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255)
    resource_type = models.CharField(
        max_length=20, choices=ResourceType.choices, default=ResourceType.OTHER
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class ResourceSchedule(BaseModel):
    resource = models.ForeignKey(
        Resource, on_delete=models.CASCADE, related_name="schedules"
    )
    day_of_week = models.PositiveSmallIntegerField(choices=Weekday.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["day_of_week", "start_time"]

    def __str__(self):
        return f"{self.resource} - {self.get_day_of_week_display()}"


class SlotHold(BaseModel):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="slot_holds",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.CASCADE,
        related_name="slot_holds",
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="slot_holds",
        null=True,
        blank=True,
    )
    resource = models.ForeignKey(
        Resource,
        on_delete=models.CASCADE,
        related_name="slot_holds",
        null=True,
        blank=True,
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    session_id = models.CharField(max_length=255)
    expires_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=["expires_at"]),
            models.Index(fields=["organization", "start_time"]),
        ]

    def __str__(self):
        return f"Hold {self.start_time:%Y-%m-%d %H:%M} ({self.session_id})"


class CancellationPolicy(BaseModel):
    class FeeType(models.TextChoices):
        NONE = "none", "None"
        FIXED = "fixed", "Fixed Amount"
        PERCENT = "percent", "Percentage"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="cancellation_policies",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.CASCADE,
        related_name="cancellation_policies",
        null=True,
        blank=True,
    )
    service = models.ForeignKey(
        "commerce.Service",
        on_delete=models.CASCADE,
        related_name="cancellation_policies",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255)
    cutoff_hours = models.PositiveIntegerField(default=24)
    fee_type = models.CharField(
        max_length=10, choices=FeeType.choices, default=FeeType.NONE
    )
    fee_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    no_show_fee_type = models.CharField(
        max_length=10, choices=FeeType.choices, default=FeeType.NONE
    )
    no_show_fee_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_refundable = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "cancellation policies"

    def __str__(self):
        return self.name


class QueueTicket(BaseModel):
    class Status(models.TextChoices):
        WAITING = "waiting", "Waiting"
        CALLED = "called", "Called"
        SERVING = "serving", "Serving"
        SERVED = "served", "Served"
        ABANDONED = "abandoned", "Abandoned"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="queue_tickets",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.CASCADE,
        related_name="queue_tickets",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        related_name="queue_tickets",
        null=True,
        blank=True,
    )
    service = models.ForeignKey(
        "commerce.Service",
        on_delete=models.SET_NULL,
        related_name="queue_tickets",
        null=True,
        blank=True,
    )
    ticket_number = models.CharField(max_length=50)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.WAITING
    )
    position = models.PositiveIntegerField(default=0)
    notified_at = models.DateTimeField(null=True, blank=True)
    serving_started_at = models.DateTimeField(null=True, blank=True)
    served_at = models.DateTimeField(null=True, blank=True)
    abandoned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["position"]
        indexes = [
            models.Index(fields=["branch", "status"]),
        ]

    def __str__(self):
        return f"{self.ticket_number} ({self.get_status_display()})"


# ---------------------------------------------------------------------------
# Payroll & commissions
# ---------------------------------------------------------------------------


class PayrollPeriod(BaseModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        PROCESSING = "processing", "Processing"
        LOCKED = "locked", "Locked"
        PAID = "paid", "Paid"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="payroll_periods",
    )
    period_start = models.DateField()
    period_end = models.DateField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )
    locked_at = models.DateTimeField(null=True, blank=True)
    locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-period_start"]

    def __str__(self):
        return f"Payroll {self.period_start} - {self.period_end}"


class CommissionEntry(BaseModel):
    class EntryType(models.TextChoices):
        COMMISSION = "commission", "Commission"
        BONUS = "bonus", "Bonus"
        DEDUCTION = "deduction", "Deduction"
        ADJUSTMENT = "adjustment", "Adjustment"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="commission_entries",
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="commission_entries"
    )
    payroll_period = models.ForeignKey(
        PayrollPeriod,
        on_delete=models.SET_NULL,
        related_name="entries",
        null=True,
        blank=True,
    )
    sale = models.ForeignKey(
        "commerce.Sale",
        on_delete=models.SET_NULL,
        related_name="commission_entries",
        null=True,
        blank=True,
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    entry_type = models.CharField(
        max_length=20, choices=EntryType.choices, default=EntryType.COMMISSION
    )
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "commission entries"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "created_at"]),
            models.Index(fields=["employee", "created_at"]),
        ]

    def __str__(self):
        return f"{self.get_entry_type_display()} {self.amount} for {self.employee}"


class CommissionRule(BaseModel):
    """Configurable commission scheme. The calculator picks the most
    specific active rule per sale item (employee+service > employee >
    service/product > org default) and writes immutable CommissionEntry
    rows; Employee.commission_rate stays as the legacy flat fallback."""

    class Basis(models.TextChoices):
        PERCENT = "percent", "Percentage of line total"
        FIXED = "fixed", "Fixed amount per item"
        TIERED = "tiered", "Tiered percentage by period revenue"

    class AppliesTo(models.TextChoices):
        SERVICES = "services", "Services"
        PRODUCTS = "products", "Products"
        ALL = "all", "Services & Products"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="commission_rules",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.CASCADE,
        related_name="commission_rules",
        null=True,
        blank=True,
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="commission_rules",
        null=True,
        blank=True,
    )
    service = models.ForeignKey(
        "commerce.Service",
        on_delete=models.CASCADE,
        related_name="commission_rules",
        null=True,
        blank=True,
    )
    product = models.ForeignKey(
        "commerce.Product",
        on_delete=models.CASCADE,
        related_name="commission_rules",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255)
    basis = models.CharField(max_length=10, choices=Basis.choices)
    rate_percent = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    fixed_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    #: Tiered basis: [{"threshold": "0", "rate_percent": "5"},
    #: {"threshold": "20000", "rate_percent": "8"}] — the highest threshold
    #: not exceeding the employee's period revenue wins.
    tiers = models.JSONField(default=list, blank=True)
    applies_to = models.CharField(
        max_length=10, choices=AppliesTo.choices, default=AppliesTo.ALL
    )
    priority = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-priority", "name"]
        indexes = [
            models.Index(fields=["organization", "is_active"]),
        ]

    def __str__(self):
        return self.name


class EmployeeCostComponent(BaseModel):
    """One recurring monthly component of an employee's fully loaded cost
    (Saudi Labor Optimization Cost Engine). Components are effective-dated,
    never edited in place for past periods — close one and open the next —
    so historical margin reports stay truthful."""

    class ComponentType(models.TextChoices):
        BASE_SALARY = "base_salary", "Base Salary"
        GOSI_EMPLOYER = "gosi_employer", "GOSI (Employer Share)"
        QIWA_VISA = "qiwa_visa", "Qiwa/Visa Amortization"
        MEDICAL_INSURANCE = "medical_insurance", "Medical Insurance"
        HOUSING = "housing", "Housing Allowance"
        TRANSPORT = "transport", "Transport Allowance"
        OTHER = "other", "Other"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="employee_cost_components",
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="cost_components"
    )
    component_type = models.CharField(max_length=30, choices=ComponentType.choices)
    monthly_amount = models.DecimalField(max_digits=12, decimal_places=2)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-effective_from"]
        indexes = [
            models.Index(fields=["employee", "effective_from"]),
        ]

    def __str__(self):
        return f"{self.get_component_type_display()} {self.monthly_amount} for {self.employee}"


class WaitlistEntry(BaseModel):
    """A customer waiting for a slot. Offers expire so high-priority
    customers cannot deadlock the list."""

    class Status(models.TextChoices):
        WAITING = "waiting", "Waiting"
        OFFERED = "offered", "Offered"
        BOOKED = "booked", "Booked"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="waitlist_entries",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.CASCADE,
        related_name="waitlist_entries",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="waitlist_entries",
    )
    service = models.ForeignKey(
        "commerce.Service",
        on_delete=models.CASCADE,
        related_name="waitlist_entries",
    )
    preferred_employee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        related_name="waitlist_entries",
        null=True,
        blank=True,
    )
    desired_from = models.DateTimeField()
    desired_until = models.DateTimeField()
    #: Higher = served first; VIP/high-LTV segments get boosted here.
    priority = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.WAITING
    )
    offered_at = models.DateTimeField(null=True, blank=True)
    offer_expires_at = models.DateTimeField(null=True, blank=True)
    booked_appointment = models.ForeignKey(
        Appointment,
        on_delete=models.SET_NULL,
        related_name="waitlist_entries",
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "waitlist entries"
        ordering = ["-priority", "created_at"]
        indexes = [
            models.Index(fields=["branch", "status"]),
        ]

    def __str__(self):
        return (
            f"{self.customer} waiting for {self.service} ({self.get_status_display()})"
        )
