from django.db import models
from django.contrib.auth.models import User
from employee.models import Employee
from base.models import Company
from chhabi.models import ChhabiModel


class Company(models.Model):
    name = models.CharField(max_length=255)
    industry = models.CharField(max_length=255, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["-created_at"]

class CRMClient(models.Model):
    STATUS_CHOICES = (
        ("lead", "Lead"),
        ("confirmed", "Confirmed Client"),
        ("long_term", "Long-Term Client"),
    )
    name = models.CharField(max_length=200)
    company_name = models.CharField(max_length=200, blank=True, null=True)
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name="contacts")
    position = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30, blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="lead")
    
    # Secure Portal Access Fields
    portal_user = models.OneToOneField(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="crm_client_profile"
    )
    is_portal_active = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.company_name or 'No Company'})"

    class Meta:
        ordering = ["-created_at"]


class Inquiry(models.Model):
    STATUS_CHOICES = (
        ("new", "New"),
        ("contacted", "Contacted"),
        ("qualified", "Qualified"),
        ("follow_up", "Follow-up"),
        ("quotation_ready", "Quotation Ready"),
        ("closed", "Closed"),
        ("archived", "Archived"),
        ("requirement_discovery", "Requirement Discovery"),
        ("quotation", "Quotation"),
        ("negotiation", "Negotiation"),
        ("confirmed_client", "Confirmed Client"),
        ("active_project", "Active Project"),
        ("payment", "Payment"),
        ("project_delivery", "Project Delivery"),
        ("successful_completion", "Successful Completion"),
        ("long_term_client", "Long-Term Client"),
    )
    client = models.ForeignKey(CRMClient, on_delete=models.CASCADE, related_name="inquiries")
    source = models.CharField(max_length=100, blank=True, null=True)
    interested_service = models.CharField(max_length=200, blank=True, null=True)
    initial_requirement = models.TextField(blank=True, null=True)
    assignee = models.ForeignKey(
        Employee, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="assigned_inquiries"
    )
    reference_number = models.CharField(max_length=30, unique=True, blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="new")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.interested_service or 'General Inquiry'} - {self.client.name}"

    class Meta:
        ordering = ["-created_at"]


class ClientRequirement(models.Model):
    PRIORITY_CHOICES = (
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    )
    APPROVAL_CHOICES = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )
    inquiry = models.ForeignKey(Inquiry, on_delete=models.CASCADE, related_name="requirements")
    project = models.ForeignKey(
        "project.Project", 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="crm_requirements"
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    modules_requested = models.TextField(blank=True, null=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="medium")
    attachment = models.FileField(upload_to="requirements/attachments/", blank=True, null=True)
    revision_number = models.IntegerField(default=1)
    approval_status = models.CharField(max_length=20, choices=APPROVAL_CHOICES, default="pending")
    assigned_team = models.ManyToManyField(Employee, blank=True, related_name="requirement_assignments")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Requirement: {self.title} for {self.inquiry.client.name}"


class RequirementRevision(models.Model):
    requirement = models.ForeignKey(ClientRequirement, on_delete=models.CASCADE, related_name="revisions")
    revision_number = models.IntegerField()
    title = models.CharField(max_length=200)
    description = models.TextField()
    modules_requested = models.TextField(blank=True, null=True)
    priority = models.CharField(max_length=20)
    attachment = models.FileField(upload_to="requirements/revisions/", blank=True, null=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Revision #{self.revision_number} of {self.requirement.title}"


class RequirementComment(models.Model):
    requirement = models.ForeignKey(ClientRequirement, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.author.username} on {self.requirement.title}"


class CRMClientAccessLog(models.Model):
    client = models.ForeignKey(CRMClient, on_delete=models.CASCADE, related_name="access_logs")
    action = models.CharField(max_length=50) # granted, revoked, login
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="client_access_actions")
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action.capitalize()} for {self.client.name}"


class Quotation(models.Model):
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("sent", "Sent"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )
    inquiry = models.ForeignKey(Inquiry, on_delete=models.CASCADE, related_name="quotations")
    quote_number = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Quote {self.quote_number} - {self.amount}"


class CRMProjectLink(models.Model):
    inquiry = models.ForeignKey(Inquiry, on_delete=models.CASCADE, related_name="projects")
    project = models.ForeignKey("project.Project", on_delete=models.CASCADE, related_name="crm_links")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.inquiry} linked to project {self.project.title}"


class CRMMeetingLink(models.Model):
    inquiry = models.ForeignKey(Inquiry, on_delete=models.CASCADE, related_name="meetings")
    meeting = models.ForeignKey("pms.Meetings", on_delete=models.CASCADE, related_name="crm_links")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.inquiry} linked to meeting {self.meeting.title}"


class CRMCommunication(models.Model):
    inquiry = models.ForeignKey(Inquiry, on_delete=models.CASCADE, related_name="communications")
    channel = models.CharField(max_length=50) # 'email', 'whatsapp', 'call', 'note'
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.channel.capitalize()} note for {self.inquiry.client.name}"


class ClientPayment(models.Model):
    inquiry = models.ForeignKey(Inquiry, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField()
    status = models.CharField(max_length=20, default="completed")
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.amount} for {self.inquiry.client.name}"


class CRMActivityLog(models.Model):
    inquiry = models.ForeignKey(Inquiry, on_delete=models.CASCADE, related_name="activity_logs")
    client = models.ForeignKey(CRMClient, on_delete=models.CASCADE, related_name="activity_logs")
    activity_type = models.CharField(max_length=50) # status_change, requirement, quotation, project, meeting, communication, payment
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Activity {self.activity_type} - {self.title}"


class InquiryNote(models.Model):
    inquiry = models.ForeignKey(Inquiry, on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Note by {self.author} on {self.inquiry}"


class Deal(models.Model):
    STAGE_CHOICES = (
        ("new", "New"),
        ("qualified", "Qualified"),
        ("proposal", "Proposal"),
        ("negotiation", "Negotiation"),
        ("won", "Won"),
        ("lost", "Lost"),
    )

    inquiry = models.OneToOneField(Inquiry, on_delete=models.CASCADE, related_name="deal")
    title = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    expected_close_date = models.DateField(null=True, blank=True)
    stage = models.CharField(max_length=50, choices=STAGE_CHOICES, default="new")
    owner = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="owned_deals")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.amount}"

    class Meta:
        ordering = ["-created_at"]


class CRMTask(models.Model):
    ACTIVITY_TYPES = (
        ("task", "Task"),
        ("call", "Call"),
        ("meeting", "Meeting"),
        ("note", "Note"),
        ("follow_up", "Follow-up"),
    )
    inquiry = models.ForeignKey(Inquiry, on_delete=models.CASCADE, related_name="tasks", null=True, blank=True)
    deal = models.ForeignKey('Deal', on_delete=models.CASCADE, related_name="tasks", null=True, blank=True)
    client = models.ForeignKey(CRMClient, on_delete=models.CASCADE, related_name="tasks", null=True, blank=True)
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES, default="task")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    due_date = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    assigned_to = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.get_activity_type_display()}: {self.title}"
        
    class Meta:
        ordering = ["due_date", "-created_at"]
