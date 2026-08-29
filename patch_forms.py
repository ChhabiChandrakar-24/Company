import os

filepath = 'crm/forms.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Add new imports
new_imports = "from crm.models import Company, Deal, CRMTask"
content = content.replace("from crm.models import (", f"{new_imports}\nfrom crm.models import (")

new_forms = """

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
"""
content += new_forms

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
