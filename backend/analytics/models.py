<<<<<<< HEAD
from django.db import models

# Create your models here.
=======
"""Analytics: raw events, reports and daily roll-up metrics."""

from django.conf import settings
from django.db import models

from core.models import BaseModel


class AnalyticsEvent(BaseModel):
    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="analytics_events",
    )
    branch = models.ForeignKey(
        "organnizations.Branch",
        on_delete=models.SET_NULL,
        related_name="analytics_events",
        null=True,
        blank=True,
    )
    event_type = models.CharField(max_length=100)
    event_data = models.JSONField(default=dict, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )
    session_id = models.CharField(max_length=255, blank=True)
    retention_months = models.PositiveSmallIntegerField(default=24)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "event_type", "created_at"]),
            models.Index(fields=["organization", "created_at"]),
        ]

    def __str__(self):
        return f"{self.event_type} @ {self.created_at:%Y-%m-%d %H:%M}"


class Report(BaseModel):
    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="reports",
    )
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=100)
    parameters = models.JSONField(default=dict, blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)
    file_url = models.URLField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class DailyMetric(BaseModel):
    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="daily_metrics",
    )
    branch = models.ForeignKey(
        "organnizations.Branch",
        on_delete=models.CASCADE,
        related_name="daily_metrics",
        null=True,
        blank=True,
    )
    date = models.DateField()
    total_appointments = models.PositiveIntegerField(default=0)
    completed_appointments = models.PositiveIntegerField(default=0)
    cancelled_appointments = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_customers = models.PositiveIntegerField(default=0)
    new_customers = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "branch", "date"],
                name="uniq_daily_metric_per_branch_date",
            )
        ]
        indexes = [
            models.Index(fields=["organization", "date"]),
        ]

    def __str__(self):
        return f"Metrics {self.organization} {self.date}"


class DailyBranchMetric(BaseModel):
    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="daily_branch_metrics",
    )
    branch = models.ForeignKey(
        "organnizations.Branch",
        on_delete=models.CASCADE,
        related_name="daily_branch_metrics",
    )
    date = models.DateField()
    total_bookings = models.PositiveIntegerField(default=0)
    completed_bookings = models.PositiveIntegerField(default=0)
    cancelled_bookings = models.PositiveIntegerField(default=0)
    no_shows = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_customers = models.PositiveIntegerField(default=0)
    new_customers = models.PositiveIntegerField(default=0)
    avg_wait_time_minutes = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )

    class Meta:
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "branch", "date"],
                name="uniq_daily_branch_metric_per_date",
            )
        ]
        indexes = [
            models.Index(fields=["branch", "date"]),
        ]

    def __str__(self):
        return f"Branch metrics {self.branch} {self.date}"


class DailyEmployeeMetric(BaseModel):
    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="daily_employee_metrics",
    )
    employee = models.ForeignKey(
        "operations.Employee",
        on_delete=models.CASCADE,
        related_name="daily_metrics",
    )
    date = models.DateField()
    total_appointments = models.PositiveIntegerField(default=0)
    completed_appointments = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_commission = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    utilization_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )

    class Meta:
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "employee", "date"],
                name="uniq_daily_employee_metric_per_date",
            )
        ]
        indexes = [
            models.Index(fields=["employee", "date"]),
        ]

    def __str__(self):
        return f"Employee metrics {self.employee} {self.date}"
>>>>>>> a3235b4 (feat(db): initialize core relational schema)
