"""Models for the quotation and payment workflow.

This app implements the workflow described by the user:
Client Requirement → Quotation → Client Review → Approval/Revision → Project Creation → Payment Schedule → Payment History.

Key features:
- Dynamic quotation number generation using a singleton ``QuotationCounter``.
- Versioning via a ``previous`` self‑foreign‑key – each revision creates a new ``Quotation`` record.
- Status tracking (`draft`, `sent`, `viewed`, `accepted`, `rejected`, `expired`, `revised`).
- Configurable payment schedule items (advance, milestone, final) – no hard‑coded percentages.
- Payment history linked to schedule entries.
- Helper methods for PDF export and status transitions.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# Import existing client and requirement models
from crm.models import CRMClient, ClientRequirement


class QuotationCounter(models.Model):
    """Singleton model to keep an atomic counter for quotation numbers.

    The ``get_next_number`` classmethod obtains a lock on the row, increments the
    ``counter`` field and returns a formatted number. Using ``select_for_update``
    ensures thread‑safety under concurrent requests.
    """

    counter = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = _("Quotation Counter")
        verbose_name_plural = _("Quotation Counters")

    @classmethod
    def get_next_number(cls) -> str:
        with transaction.atomic():
            # ``select_for_update`` creates a row lock
            counter_obj, _ = cls.objects.select_for_update().get_or_create(pk=1)
            counter_obj.counter += 1
            counter_obj.save()
            # Format: Q-YYYYMMDD-XXXX where XXXX is zero‑padded counter
            today_str = timezone.now().strftime("%Y%m%d")
            return f"Q-{today_str}-{counter_obj.counter:04d}"


class Quotation(models.Model):
    """Represents a quotation issued to a client.

    The model is deliberately lightweight – detailed line items can be added in a
    separate model if required. For the current specification we store a JSON field
    ``details`` that captures modules/features, pricing, taxes, discounts and any
    free‑form terms.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        SENT = "sent", _("Sent")
        VIEWED = "viewed", _("Viewed")
        ACCEPTED = "accepted", _("Accepted")
        REJECTED = "rejected", _("Rejected")
        EXPIRED = "expired", _("Expired")
        REVISED = "revised", _("Revised")

    # Core relations
    client = models.ForeignKey(CRMClient, on_delete=models.CASCADE, related_name="quotations")
    requirement = models.ForeignKey(
        ClientRequirement, on_delete=models.SET_NULL, null=True, blank=True, related_name="quotations"
    )

    # Business fields
    number = models.CharField(max_length=30, unique=True, editable=False)
    title = models.CharField(max_length=200, help_text=_("A short title for the quotation"))
    details = models.JSONField(
        default=dict,
        help_text=_(
            "Arbitrary JSON containing modules/features, pricing, taxes, discounts, terms, etc."
        ),
    )
    validity_date = models.DateField(null=True, blank=True, help_text=_("Date until which the quotation is valid"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Versioning
    previous = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="revisions"
    )

    status = models.CharField(max_length=15, choices=Status.choices, default=Status.DRAFT)
    project_master = models.ForeignKey('masters.ProjectMaster', on_delete=models.SET_NULL, null=True, blank=True, related_name='quotations')

    def __str__(self) -> str:
        return f"{self.number} – {self.client.name}"

    def save(self, *args, **kwargs):
        if not self.pk:
            # New quotation – generate a number
            self.number = QuotationCounter.get_next_number()
        super().save(*args, **kwargs)

    def mark_sent(self):
        self.status = self.Status.SENT
        self.save(update_fields=["status"])  # type: ignore[arg-type]

    def mark_viewed(self):
        self.status = self.Status.VIEWED
        self.save(update_fields=["status"])  # type: ignore[arg-type]

    def accept(self):
        self.status = self.Status.ACCEPTED
        self.save(update_fields=["status"])  # type: ignore[arg-type]

    def reject(self):
        self.status = self.Status.REJECTED
        self.save(update_fields=["status"])  # type: ignore[arg-type]

    def expire(self):
        self.status = self.Status.EXPIRED
        self.save(update_fields=["status"])  # type: ignore[arg-type]

    def revise(self, new_details: dict) -> "Quotation":
        """Create a revised copy of the quotation.

        The current instance becomes the ``previous`` of the new revision and its
        status is switched to ``revised``.
        """
        self.status = self.Status.REVISED
        self.save(update_fields=["status"])  # type: ignore[arg-type]
        revision = Quotation.objects.create(
            client=self.client,
            requirement=self.requirement,
            title=self.title,
            details=new_details,
            validity_date=self.validity_date,
            previous=self,
        )
        return revision


class QuotationPaymentSchedule(models.Model):
    """Configurable payment schedule linked to a quotation.

    ``due_date`` can be absolute or calculated from the quotation's creation
    date. ``amount`` may be a fixed value or a percentage of the total – the UI
    will enforce that the sum of schedule amounts equals the quotation total.
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        PAID = "paid", _("Paid")
        OVERDUE = "overdue", _("Overdue")

    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name="schedules")
    description = models.CharField(max_length=200, help_text=_("Description of the payment milestone"))
    due_date = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)

    def __str__(self) -> str:
        return f"{self.quotation.number} – {self.description} ({self.amount})"

    def mark_paid(self):
        self.status = self.Status.PAID
        self.save(update_fields=["status"])  # type: ignore[arg-type]


class QuotationPayment(models.Model):
    """Record of an actual payment made against a schedule item.

    ``gateway_reference`` stores an identifier from the integrated payment gateway.
    """

    schedule = models.ForeignKey(
        QuotationPaymentSchedule, on_delete=models.CASCADE, related_name="payments"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField(default=timezone.now)
    gateway_reference = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Payment {self.amount} for {self.schedule}" 

    class Meta:
        verbose_name = _("Quotation Payment")
        verbose_name_plural = _("Quotation Payments")


# Helper function to compute total amount from quotation details
def compute_quotation_total(details: dict) -> Decimal:
    """Calculate the total amount for a quotation.

    Expected ``details`` format (example)::

        {
            "modules": [{"name": "Feature A", "price": "1000.00"}, ...],
            "tax": "0.10",          # 10 % tax as a decimal string
            "discount": "50.00",   # flat discount
        }
    """
    total = Decimal("0")
    for module in details.get("modules", []):
        price = Decimal(module.get("price", "0"))
        total += price
    tax_rate = Decimal(details.get("tax", "0"))
    discount = Decimal(details.get("discount", "0"))
    total = total + (total * tax_rate) - discount
    return total.quantize(Decimal("0.01"))
