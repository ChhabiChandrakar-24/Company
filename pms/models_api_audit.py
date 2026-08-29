from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

class ApiAuditLog(models.Model):
    api_key = models.ForeignKey('DeveloperApiKey', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    endpoint = models.CharField(max_length=200)
    method = models.CharField(max_length=10)
    status_code = models.IntegerField()
    request_body = models.TextField(null=True, blank=True)
    response_body = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "API Audit Log"
        verbose_name_plural = "API Audit Logs"

class DeveloperWebhook(models.Model):
    api_key = models.ForeignKey('DeveloperApiKey', on_delete=models.CASCADE)
    event_type = models.CharField(max_length=50)
    target_url = models.URLField()
    secret = models.CharField(max_length=128)
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Developer Webhook"
        verbose_name_plural = "Developer Webhooks"
