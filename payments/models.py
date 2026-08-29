from django.db import models

class PaymentTransaction(models.Model):
    PAYMENT_STATUS_CHOICES = (
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    )
    provider = models.CharField(max_length=30)
    external_payment_id = models.CharField(max_length=255, unique=True)
    user_subscription = models.ForeignKey('pms.UserSubscription', on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    webhook_processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.provider} - {self.external_payment_id} ({self.status})"
