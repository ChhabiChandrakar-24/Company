from django.db import models
from django.utils.translation import gettext_lazy as _


class ProjectMaster(models.Model):
    """Master definition of a project/template."""

    code = models.CharField(max_length=50, unique=True, help_text=_("Project Code"))
    name = models.CharField(max_length=200, help_text=_("Project Name"))
    category = models.CharField(max_length=100, blank=True, help_text=_("Project Category"))
    short_description = models.CharField(max_length=255, blank=True)
    detailed_description = models.TextField(blank=True)
    default_estimated_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    min_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    max_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    default_tax_configuration = models.CharField(max_length=100, blank=True)
    default_payment_plan = models.ForeignKey('PaymentPlanTemplate', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    validity_info = models.CharField(max_length=200, blank=True, help_text=_("Project Validity / Delivery Information"))
    status = models.CharField(max_length=20, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Project Master')
        verbose_name_plural = _('Project Masters')

    def __str__(self):
        return f"{self.code} - {self.name}"


class ServiceMaster(models.Model):
    """Reusable service/feature library."""

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    default_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Service Master')
        verbose_name_plural = _('Service Masters')

    def __str__(self):
        return f"{self.code} - {self.name}"


class ProjectMasterFeature(models.Model):
    """Association of a ServiceMaster with a ProjectMaster, with extra configuration."""

    project = models.ForeignKey(ProjectMaster, on_delete=models.CASCADE, related_name='features')
    service = models.ForeignKey(ServiceMaster, on_delete=models.PROTECT, related_name='project_links')
    feature_name = models.CharField(max_length=200, blank=True)
    feature_code = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    default_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, default='active')
    optional = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = _('Project Master Feature')
        verbose_name_plural = _('Project Master Features')
        ordering = ['display_order']

    def __str__(self):
        return f"{self.project.code} - {self.service.code}"


class PaymentPlanTemplate(models.Model):
    """Template for payment milestones (percentage or amount)."""

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = _('Payment Plan Template')
        verbose_name_plural = _('Payment Plan Templates')

    def __str__(self):
        return self.name


class PaymentPlanMilestone(models.Model):
    """Milestone definition belonging to a PaymentPlanTemplate."""

    plan = models.ForeignKey(PaymentPlanTemplate, on_delete=models.CASCADE, related_name='milestones')
    description = models.CharField(max_length=200)
    # amount can be a fixed value or a percentage of total – store as decimal. Positive for fixed, between 0-100 for percentage.
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    is_percentage = models.BooleanField(default=False)
    due_days = models.PositiveIntegerField(help_text=_('Number of days from quotation creation'))

    class Meta:
        verbose_name = _('Payment Plan Milestone')
        verbose_name_plural = _('Payment Plan Milestones')
        ordering = ['id']

    def __str__(self):
        pct = '%' if self.is_percentage else ''
        return f"{self.description} - {self.amount}{pct}"
