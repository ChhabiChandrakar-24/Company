from django.contrib import admin
from .models import ProjectMaster, ServiceMaster, ProjectMasterFeature, PaymentPlanTemplate, PaymentPlanMilestone

@admin.register(ProjectMaster)
class ProjectMasterAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "category", "status", "created_at")
    search_fields = ("code", "name", "category")
    list_filter = ("status",)

@admin.register(ServiceMaster)
class ServiceMasterAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "default_price", "created_at")
    search_fields = ("code", "name")
    list_filter = ("default_price",)

@admin.register(ProjectMasterFeature)
class ProjectMasterFeatureAdmin(admin.ModelAdmin):
    list_display = ("project", "service", "feature_name", "default_price", "quantity", "status", "optional")
    search_fields = ("project__code", "service__code", "feature_name")
    list_filter = ("status", "optional")

@admin.register(PaymentPlanTemplate)
class PaymentPlanTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)

@admin.register(PaymentPlanMilestone)
class PaymentPlanMilestoneAdmin(admin.ModelAdmin):
    list_display = ("plan", "description", "amount", "is_percentage", "due_days")
    search_fields = ("plan__name", "description")
    list_filter = ("is_percentage",)
