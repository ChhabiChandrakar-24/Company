from django.db import models
from django import forms
from crm.models import (
    Inquiry,
    InquiryNote,
    Company,
    Deal,
    CRMTask,
    CRMClient,
    ClientRequirement,
    RequirementComment,
    Quotation,
    CRMCommunication,
    ClientPayment,
    CRMProjectLink,
    CRMMeetingLink,
)
from employee.models import Employee
from project.models import Project
from pms.models import Meetings

class InquiryForm(forms.ModelForm):
    client_name = forms.CharField(
        max_length=200, 
        label="Client Name", 
        widget=forms.TextInput(attrs={"class": "form-control"})
    )
    company_name = forms.CharField(
        max_length=200, 
        required=False, 
        label="Company Name", 
        widget=forms.TextInput(attrs={"class": "form-control"})
    )
    email = forms.EmailField(
        label="Email Address", 
        widget=forms.EmailInput(attrs={"class": "form-control"})
    )
    phone = forms.CharField(
        max_length=30, 
        required=False, 
        label="Phone Number", 
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    reference_number = forms.CharField(
        max_length=30,
        required=False,
        label="Reference Number",
        widget=forms.TextInput(attrs={"class": "form-control", "readonly": "readonly"})
    )

    class Meta:
        model = Inquiry
        fields = [
            "reference_number",
            "source",
            "interested_service",
            "initial_requirement",
            "assignee",
            "status",
        ]
        widgets = {
            "source": forms.TextInput(attrs={"class": "form-control"}),
            "interested_service": forms.TextInput(attrs={"class": "form-control"}),
            "initial_requirement": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "assignee": forms.Select(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        phone = cleaned_data.get('phone')
        # Check for existing client with same email or phone (open inquiries only)
        from crm.models import CRMClient
        duplicates = CRMClient.objects.filter(
            models.Q(email=email) | models.Q(phone=phone)
        ).exclude(status__in=["closed", "archived", "lost", "won"])
        if duplicates.exists():
            raise forms.ValidationError(
                "A client with this email or phone already exists. Please review existing inquiries before creating a new one."
            )
        return cleaned_data

class InquiryNoteForm(forms.ModelForm):
    class Meta:
        model = InquiryNote
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class ClientRequirementForm(forms.ModelForm):
    class Meta:
        model = ClientRequirement
        fields = ["title", "description"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class ClientRequirementAdvancedForm(forms.ModelForm):
    class Meta:
        model = ClientRequirement
        fields = ["title", "description", "modules_requested", "priority", "attachment", "approval_status", "assigned_team", "project"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "modules_requested": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "e.g., Auth, Cart, Payments"}),
            "priority": forms.Select(attrs={"class": "form-control"}),
            "attachment": forms.FileInput(attrs={"class": "form-control"}),
            "approval_status": forms.Select(attrs={"class": "form-control"}),
            "assigned_team": forms.SelectMultiple(attrs={"class": "form-control"}),
            "project": forms.Select(attrs={"class": "form-control"}),
        }


class RequirementCommentForm(forms.ModelForm):
    class Meta:
        model = RequirementComment
        fields = ["comment"]
        widgets = {
            "comment": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Write a comment..."}),
        }


class CRMMeetingSchedulerForm(forms.ModelForm):
    class Meta:
        model = Meetings
        fields = ["title", "date", "end_date", "description", "meeting_type", "provider", "employee_id"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "date": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
            "end_date": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "meeting_type": forms.Select(attrs={"class": "form-control"}),
            "provider": forms.Select(attrs={"class": "form-control"}),
            "employee_id": forms.SelectMultiple(attrs={"class": "form-control"}),
        }


class QuotationForm(forms.ModelForm):
    class Meta:
        model = Quotation
        fields = ["quote_number", "amount", "description", "status"]
        widgets = {
            "quote_number": forms.TextInput(attrs={"class": "form-control"}),
            "amount": forms.NumberInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "status": forms.Select(attrs={"class": "form-control"}),
        }


class CRMCommunicationForm(forms.ModelForm):
    class Meta:
        model = CRMCommunication
        fields = ["channel", "message"]
        widgets = {
            "channel": forms.Select(
                choices=(
                    ("email", "Email"),
                    ("whatsapp", "WhatsApp"),
                    ("call", "Call"),
                    ("note", "Note/Internal Comment"),
                ),
                attrs={"class": "form-control"}
            ),
            "message": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class ClientPaymentForm(forms.ModelForm):
    class Meta:
        model = ClientPayment
        fields = ["amount", "payment_date", "status", "reference_number"]
        widgets = {
            "amount": forms.NumberInput(attrs={"class": "form-control"}),
            "payment_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "status": forms.Select(
                choices=(
                    ("pending", "Pending"),
                    ("completed", "Completed"),
                    ("failed", "Failed"),
                ),
                attrs={"class": "form-control"}
            ),
            "reference_number": forms.TextInput(attrs={"class": "form-control"}),
        }


class CRMProjectLinkForm(forms.ModelForm):
    class Meta:
        model = CRMProjectLink
        fields = ["project"]
        widgets = {
            "project": forms.Select(attrs={"class": "form-control"}),
        }


class CRMMeetingLinkForm(forms.ModelForm):
    class Meta:
        model = CRMMeetingLink
        fields = ["meeting"]
        widgets = {
            "meeting": forms.Select(attrs={"class": "form-control"}),
        }


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ["name", "industry", "website", "address"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "industry": forms.TextInput(attrs={"class": "form-control"}),
            "website": forms.URLInput(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

class DealForm(forms.ModelForm):
    class Meta:
        model = Deal
        fields = ["title", "amount", "expected_close_date", "stage", "owner"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "amount": forms.NumberInput(attrs={"class": "form-control"}),
            "expected_close_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "stage": forms.Select(attrs={"class": "form-control"}),
            "owner": forms.Select(attrs={"class": "form-control"}),
        }

class CRMTaskForm(forms.ModelForm):
    class Meta:
        model = CRMTask
        fields = ["activity_type", "title", "description", "due_date", "assigned_to"]
        widgets = {
            "activity_type": forms.Select(attrs={"class": "form-control"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "due_date": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
            "assigned_to": forms.Select(attrs={"class": "form-control"}),
        }
