"""
admin.py
"""

from django.contrib import admin

from chhabi_audit.models import AuditTag, ChhabiAuditInfo, ChhabiAuditLog

# Register your models here.

admin.site.register(AuditTag)
