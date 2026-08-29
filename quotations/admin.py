"""Admin registration for the quotations app.

Provides list display, filters and readonly fields for the core models.
"""

from django.contrib import admin
from .models import Quotation, QuotationPaymentSchedule, QuotationPayment, QuotationCounter

@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ("number", "client", "title", "status", "validity_date", "created_at")
    list_filter = ("status", "validity_date", "created_at")
    readonly_fields = ("number", "created_at", "updated_at")
    search_fields = ("number", "client__name", "title")

@admin.register(QuotationPaymentSchedule)
class QuotationPaymentScheduleAdmin(admin.ModelAdmin):
    list_display = ("quotation", "description", "due_date", "amount", "status")
    list_filter = ("status", "due_date")
    readonly_fields = ("quotation",)
    search_fields = ("quotation__number", "description")

@admin.register(QuotationPayment)
class QuotationPaymentAdmin(admin.ModelAdmin):
    list_display = ("schedule", "amount", "payment_date", "gateway_reference")
    list_filter = ("payment_date",)
    readonly_fields = ("schedule", "payment_date", "created_at")
    search_fields = ("schedule__quotation__number", "gateway_reference")

@admin.register(QuotationCounter)
class QuotationCounterAdmin(admin.ModelAdmin):
    list_display = ("counter",)
    readonly_fields = ("counter",)
