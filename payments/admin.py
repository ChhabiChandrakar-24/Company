from django.contrib import admin

from .models import PaymentTransaction


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "provider",
        "external_payment_id",
        "user_subscription",
        "amount",
        "currency",
        "status",
        "created_at",
        "webhook_processed_at",
    )
    list_filter = ("provider", "status", "currency")
    search_fields = ("external_payment_id",)
    readonly_fields = ("created_at", "updated_at", "webhook_processed_at")
