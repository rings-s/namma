<<<<<<< HEAD
from django.db import models

# Create your models here.
=======
"""Customers: profiles, preferences, clinical notes and documents."""

from django.conf import settings
from django.db import models

from core.models import BaseModel, Channel, SoftDeleteModel


class Customer(SoftDeleteModel, BaseModel):
    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        OTHER = "other", "Other"

    class Source(models.TextChoices):
        WALK_IN = "walk_in", "Walk-in"
        ONLINE = "online", "Online"
        PHONE = "phone", "Phone"
        REFERRAL = "referral", "Referral"
        SOCIAL = "social", "Social Media"
        IMPORT = "import", "Imported"
        OTHER = "other", "Other"

    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="customers",
    )
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.CharField(max_length=500, blank=True)
    city = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    source = models.CharField(
        max_length=20, choices=Source.choices, default=Source.WALK_IN
    )
    loyalty_points = models.PositiveIntegerField(default=0)
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    visit_count = models.PositiveIntegerField(default=0)
    last_visit_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["organization", "phone"]),
            models.Index(fields=["organization", "created_at"]),
            models.Index(fields=["organization", "is_active"]),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip()


class CustomerPreference(BaseModel):
    customer = models.OneToOneField(
        Customer, on_delete=models.CASCADE, related_name="preferences"
    )
    preferred_branch = models.ForeignKey(
        "organnizations.Branch",
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )
    preferred_employee = models.ForeignKey(
        "operations.Employee",
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )
    communication_channel = models.CharField(
        max_length=20, choices=Channel.choices, default=Channel.WHATSAPP
    )
    marketing_opt_in = models.BooleanField(default=False)
    reminder_opt_in = models.BooleanField(default=True)

    def __str__(self):
        return f"Preferences for {self.customer}"


class ClinicalNote(BaseModel):
    class NoteType(models.TextChoices):
        SOAP = "soap", "SOAP"
        TREATMENT = "treatment", "Treatment"
        CONSULTATION = "consultation", "Consultation"
        GENERAL = "general", "General"

    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="clinical_notes",
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="clinical_notes"
    )
    appointment = models.ForeignKey(
        "operations.Appointment",
        on_delete=models.SET_NULL,
        related_name="clinical_notes",
        null=True,
        blank=True,
    )
    employee = models.ForeignKey(
        "operations.Employee",
        on_delete=models.SET_NULL,
        related_name="clinical_notes",
        null=True,
        blank=True,
    )
    note_type = models.CharField(
        max_length=20, choices=NoteType.choices, default=NoteType.GENERAL
    )
    content_encrypted = models.TextField()
    is_sensitive = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "created_at"]),
        ]

    def __str__(self):
        return f"{self.get_note_type_display()} note for {self.customer}"


class CustomerDocument(BaseModel):
    organization = models.ForeignKey(
        "organnizations.Organization",
        on_delete=models.CASCADE,
        related_name="customer_documents",
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="documents"
    )
    document_type = models.CharField(max_length=100)
    file_url_encrypted = models.CharField(max_length=1024)
    is_sensitive = models.BooleanField(default=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.document_type} for {self.customer}"
>>>>>>> a3235b4 (feat(db): initialize core relational schema)
