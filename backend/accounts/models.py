"""Accounts: custom user model, per-organization roles and TOTP 2FA."""

import uuid

import pyotp
from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone

from core.models import BaseModel


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("The email address must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    avatar_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        ordering = ["email"]

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email

    def get_short_name(self):
        return self.first_name or self.email


class UserRole(BaseModel):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        MANAGER = "manager", "Manager"
        RECEPTIONIST = "receptionist", "Receptionist"
        STAFF = "staff", "Staff"
        ACCOUNTANT = "accountant", "Accountant"
        MARKETER = "marketer", "Marketer"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="roles")
    role = models.CharField(max_length=20, choices=Role.choices)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="user_roles",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.CASCADE,
        related_name="user_roles",
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "organization", "branch", "role"],
                name="uniq_user_role_per_org_branch",
            )
        ]
        indexes = [
            models.Index(fields=["organization", "role"]),
        ]

    def __str__(self):
        return f"{self.user} as {self.get_role_display()} @ {self.organization}"


class UserSession(BaseModel):
    """One refresh-token lineage: created at login, its jti re-pointed on
    every rotation, ended by logout/revocation. Powers the active-session
    dashboard and remote sign-out."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    refresh_jti = models.CharField(max_length=64, unique=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    device_label = models.CharField(max_length=255, blank=True)
    last_seen_at = models.DateTimeField(default=timezone.now)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-last_seen_at"]
        indexes = [
            models.Index(fields=["user", "revoked_at"]),
        ]

    def __str__(self):
        state = "revoked" if self.revoked_at else "active"
        return f"Session for {self.user} ({state})"


class TwoFactorDevice(BaseModel):
    """TOTP device for a user. 2FA is enforced at login once ``confirmed``."""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="two_factor_device"
    )
    secret = models.CharField(max_length=64, editable=False)
    confirmed = models.BooleanField(default=False)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        state = "confirmed" if self.confirmed else "pending"
        return f"2FA device for {self.user} ({state})"

    @classmethod
    def generate_secret(cls):
        return pyotp.random_base32()

    def verify(self, code):
        # valid_window=1 tolerates one 30s step of clock drift either side.
        return pyotp.TOTP(self.secret).verify(code, valid_window=1)

    def provisioning_uri(self):
        issuer = getattr(settings, "TWO_FACTOR_ISSUER", "Namaa")
        return pyotp.TOTP(self.secret).provisioning_uri(
            name=self.user.email, issuer_name=issuer
        )

    def confirm(self):
        self.confirmed = True
        self.confirmed_at = timezone.now()
        self.save(update_fields=["confirmed", "confirmed_at", "updated_at"])
