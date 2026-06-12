"""Commerce: service catalog, products, point-of-sale sales and stored value.

Stored value (gift cards, store credit, packages) follows the platform's
money rules: every balance change is an append-only transaction row, and
balances are mutated only under ``select_for_update``.
"""

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from core.models import BaseModel, SoftDeleteModel


class ServiceCategory(BaseModel):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="service_categories",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "service categories"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Service(BaseModel):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="services",
    )
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.SET_NULL,
        related_name="services",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(default=30)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["organization", "is_active"]),
        ]

    def __str__(self):
        return self.name


class Product(SoftDeleteModel, BaseModel):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="products",
    )
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    stock_quantity = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["organization", "sku"]),
            models.Index(fields=["organization", "is_active"]),
        ]

    def __str__(self):
        return self.name


class Sale(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="sales",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.CASCADE,
        related_name="sales",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        related_name="sales",
        null=True,
        blank=True,
    )
    employee = models.ForeignKey(
        "operations.Employee",
        on_delete=models.SET_NULL,
        related_name="sales",
        null=True,
        blank=True,
    )
    appointment = models.ForeignKey(
        "operations.Appointment",
        on_delete=models.SET_NULL,
        related_name="sales",
        null=True,
        blank=True,
    )
    sale_number = models.CharField(max_length=50, unique=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "created_at"]),
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["branch", "created_at"]),
        ]

    def __str__(self):
        return self.sale_number


class SaleItem(BaseModel):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="items")
    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        related_name="sale_items",
        null=True,
        blank=True,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        related_name="sale_items",
        null=True,
        blank=True,
    )
    description = models.CharField(max_length=500, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.sale} - {self.description or self.quantity}"


class GiftCard(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        DEPLETED = "depleted", "Depleted"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="gift_cards",
    )
    code = models.CharField(max_length=32)
    purchased_by = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        related_name="gift_cards_purchased",
        null=True,
        blank=True,
    )
    sale = models.ForeignKey(
        Sale,
        on_delete=models.SET_NULL,
        related_name="gift_cards",
        null=True,
        blank=True,
    )
    initial_value = models.DecimalField(max_digits=12, decimal_places=2)
    balance = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"], name="uniq_gift_card_code_per_org"
            ),
            models.CheckConstraint(
                condition=models.Q(balance__gte=0), name="gift_card_balance_gte_0"
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "status"]),
        ]

    def __str__(self):
        return f"Gift card {self.code} ({self.balance})"

    def redeem(self, amount, sale=None, created_by=None):
        """Atomically deduct ``amount``; returns the appended transaction."""
        if amount <= 0:
            raise ValidationError("Redemption amount must be positive.")
        with transaction.atomic():
            card = GiftCard.objects.select_for_update().get(pk=self.pk)
            if card.status != self.Status.ACTIVE:
                raise ValidationError("This gift card is not active.")
            if card.expires_at is not None and card.expires_at < timezone.now():
                raise ValidationError("This gift card has expired.")
            if amount > card.balance:
                raise ValidationError("Redemption amount exceeds the card balance.")
            card.balance -= amount
            if card.balance == 0:
                card.status = self.Status.DEPLETED
            card.save(update_fields=["balance", "status", "updated_at"])
            self.balance, self.status = card.balance, card.status
            return GiftCardTransaction.objects.create(
                gift_card=card,
                transaction_type=GiftCardTransaction.Type.REDEMPTION,
                amount=amount,
                balance_after=card.balance,
                sale=sale,
                created_by=created_by,
            )


class GiftCardTransaction(BaseModel):
    """Append-only gift card ledger; rows are never updated or deleted."""

    class Type(models.TextChoices):
        ISSUE = "issue", "Issue"
        REDEMPTION = "redemption", "Redemption"
        REFUND = "refund", "Refund"
        ADJUSTMENT = "adjustment", "Adjustment"
        EXPIRY = "expiry", "Expiry"

    gift_card = models.ForeignKey(
        GiftCard, on_delete=models.CASCADE, related_name="transactions"
    )
    transaction_type = models.CharField(max_length=20, choices=Type.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    sale = models.ForeignKey(
        Sale,
        on_delete=models.SET_NULL,
        related_name="gift_card_transactions",
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="gift_card_transactions",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["gift_card", "created_at"]),
        ]

    def __str__(self):
        return (
            f"{self.get_transaction_type_display()} {self.amount} on {self.gift_card}"
        )


class StoreCreditAccount(BaseModel):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="store_credit_accounts",
    )
    customer = models.OneToOneField(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="store_credit_account",
    )
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(balance__gte=0), name="store_credit_balance_gte_0"
            ),
        ]

    def __str__(self):
        return f"Store credit for {self.customer} ({self.balance})"

    def apply(
        self, transaction_type, amount, sale=None, created_by=None, description=""
    ):
        """Atomically credit or debit; returns the appended transaction."""
        if amount <= 0:
            raise ValidationError("Amount must be positive.")
        debit_types = (
            StoreCreditTransaction.Type.DEBIT,
            StoreCreditTransaction.Type.EXPIRY,
        )
        with transaction.atomic():
            account = StoreCreditAccount.objects.select_for_update().get(pk=self.pk)
            delta = -amount if transaction_type in debit_types else amount
            if account.balance + delta < 0:
                raise ValidationError("Amount exceeds the store credit balance.")
            account.balance += delta
            account.save(update_fields=["balance", "updated_at"])
            self.balance = account.balance
            return StoreCreditTransaction.objects.create(
                account=account,
                transaction_type=transaction_type,
                amount=amount,
                balance_after=account.balance,
                sale=sale,
                created_by=created_by,
                description=description,
            )


class StoreCreditTransaction(BaseModel):
    """Append-only store credit ledger; rows are never updated or deleted."""

    class Type(models.TextChoices):
        CREDIT = "credit", "Credit"
        DEBIT = "debit", "Debit"
        REFUND = "refund", "Refund"
        EXPIRY = "expiry", "Expiry"

    account = models.ForeignKey(
        StoreCreditAccount, on_delete=models.CASCADE, related_name="transactions"
    )
    transaction_type = models.CharField(max_length=20, choices=Type.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    sale = models.ForeignKey(
        Sale,
        on_delete=models.SET_NULL,
        related_name="store_credit_transactions",
        null=True,
        blank=True,
    )
    description = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="store_credit_transactions",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["account", "created_at"]),
        ]

    def __str__(self):
        return f"{self.get_transaction_type_display()} {self.amount} on {self.account}"


class Package(BaseModel):
    """A sellable bundle, membership or prepaid block of services."""

    class PackageType(models.TextChoices):
        BUNDLE = "bundle", "Bundle"
        MEMBERSHIP = "membership", "Membership"
        PREPAID = "prepaid", "Prepaid"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="packages",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    package_type = models.CharField(
        max_length=20, choices=PackageType.choices, default=PackageType.BUNDLE
    )
    price = models.DecimalField(max_digits=12, decimal_places=2)
    validity_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Days until a purchased package expires; blank = never.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["organization", "is_active"]),
        ]

    def __str__(self):
        return self.name


class PackageItem(BaseModel):
    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name="items")
    service = models.ForeignKey(
        Service, on_delete=models.PROTECT, related_name="package_items"
    )
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["package", "service"], name="uniq_service_per_package"
            ),
        ]

    def __str__(self):
        return f"{self.quantity}x {self.service} in {self.package}"


class CustomerPackage(BaseModel):
    """A customer's purchased instance of a package."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CONSUMED = "consumed", "Consumed"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="customer_packages",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="packages",
    )
    package = models.ForeignKey(
        Package, on_delete=models.PROTECT, related_name="customer_packages"
    )
    sale = models.ForeignKey(
        Sale,
        on_delete=models.SET_NULL,
        related_name="customer_packages",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    starts_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["customer", "status"]),
        ]

    def __str__(self):
        return f"{self.package} for {self.customer}"

    def remaining_quantity(self, package_item):
        used = (
            self.redemptions.filter(package_item=package_item).aggregate(
                total=models.Sum("quantity")
            )["total"]
            or 0
        )
        return package_item.quantity - used

    def redeem(self, package_item, quantity=1, appointment=None, created_by=None):
        """Atomically consume entitlements; returns the appended redemption."""
        if quantity <= 0:
            raise ValidationError("Redemption quantity must be positive.")
        if package_item.package_id != self.package_id:
            raise ValidationError(
                "This item does not belong to the customer's package."
            )
        with transaction.atomic():
            owned = CustomerPackage.objects.select_for_update().get(pk=self.pk)
            if owned.status != self.Status.ACTIVE:
                raise ValidationError("This package is not active.")
            if owned.expires_at is not None and owned.expires_at < timezone.now():
                raise ValidationError("This package has expired.")
            if quantity > owned.remaining_quantity(package_item):
                raise ValidationError("Not enough remaining uses on this package item.")
            redemption = PackageRedemption.objects.create(
                customer_package=owned,
                package_item=package_item,
                quantity=quantity,
                appointment=appointment,
                created_by=created_by,
            )
            fully_consumed = all(
                owned.remaining_quantity(item) == 0
                for item in owned.package.items.all()
            )
            if fully_consumed:
                owned.status = self.Status.CONSUMED
                owned.save(update_fields=["status", "updated_at"])
                self.status = owned.status
            return redemption


class PackageRedemption(BaseModel):
    """Append-only record of package entitlement usage."""

    customer_package = models.ForeignKey(
        CustomerPackage, on_delete=models.CASCADE, related_name="redemptions"
    )
    package_item = models.ForeignKey(
        PackageItem, on_delete=models.PROTECT, related_name="redemptions"
    )
    quantity = models.PositiveIntegerField(default=1)
    appointment = models.ForeignKey(
        "operations.Appointment",
        on_delete=models.SET_NULL,
        related_name="package_redemptions",
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        related_name="package_redemptions",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer_package", "created_at"]),
        ]

    def __str__(self):
        return f"{self.quantity}x {self.package_item} redeemed"


# ---------------------------------------------------------------------------
# Dynamic pricing
# ---------------------------------------------------------------------------


class PricingRule(BaseModel):
    """One dynamic-pricing adjustment. The resolver picks the highest-
    priority active rule matching the sale context (time window, weekday,
    customer segment) and applies its adjustment to the base price; demand-
    based rules are driven by the utilization the caller measured."""

    class RuleType(models.TextChoices):
        TIME_BASED = "time_based", "Time-Based"
        DEMAND_BASED = "demand_based", "Demand-Based"
        SEGMENT_BASED = "segment_based", "Segment-Based"

    class AdjustmentType(models.TextChoices):
        PERCENT = "percent", "Percentage"
        FIXED = "fixed", "Fixed Amount"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="pricing_rules",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.CASCADE,
        related_name="pricing_rules",
        null=True,
        blank=True,
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="pricing_rules",
        null=True,
        blank=True,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="pricing_rules",
        null=True,
        blank=True,
    )
    segment = models.ForeignKey(
        "customers.CustomerSegment",
        on_delete=models.CASCADE,
        related_name="pricing_rules",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255)
    rule_type = models.CharField(max_length=20, choices=RuleType.choices)
    adjustment_type = models.CharField(
        max_length=10, choices=AdjustmentType.choices, default=AdjustmentType.PERCENT
    )
    #: Signed: -20 percent = happy-hour discount, +15 = peak surcharge.
    adjustment_value = models.DecimalField(max_digits=12, decimal_places=2)
    #: ISO weekday ints (1=Mon .. 7=Sun); empty = every day.
    days_of_week = models.JSONField(default=list, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    #: Demand-based bounds on measured slot utilization (0-100).
    min_utilization_percent = models.PositiveSmallIntegerField(null=True, blank=True)
    max_utilization_percent = models.PositiveSmallIntegerField(null=True, blank=True)
    priority = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-priority", "name"]
        indexes = [
            models.Index(fields=["organization", "is_active"]),
        ]

    def __str__(self):
        return self.name
