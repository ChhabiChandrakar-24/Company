# communications/models.py

from django.db import models
from django.contrib.auth.models import User
from base.models import Company

class CommunicationLog(models.Model):
    CHANNEL_CHOICES = (
        ("email", "Email"),
        ("whatsapp", "WhatsApp"),
    )
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    client = models.ForeignKey('crm.CRMClient', on_delete=models.CASCADE, related_name='communication_logs', null=True, blank=True)
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField()
    status = models.CharField(max_length=20)  # e.g., sent, failed
    response_data = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # optional link to email log for backward compatibility
    email_log = models.ForeignKey('base.EmailLog', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, editable=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Communication Log"
        verbose_name_plural = "Communication Logs"

    def __str__(self):
        return f"{self.channel} to {self.client.email} at {self.created_at}"
