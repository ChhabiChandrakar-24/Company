from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import models
from django.forms import modelform_factory
from django.http import FileResponse, Http404
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date

from chhabi_api.models import MobileAttendanceEvidence
from employee.models import Employee

from .models import (
    FooterLink, FooterSection, FooterSocialLink, JobOpening, PricingPlan, TeamMember,
    WebsitePage, WebsiteSection, WebsiteService, WebsiteSettings, WebsiteSubmission,
)


CONFIG = {
    "pages": (WebsitePage, "Website Pages", ("title", "slug", "is_published", "updated_at"), None),
    "sections": (WebsiteSection, "Page Sections", ("heading", "page", "section_type", "is_active", "sort_order"), None),
    "services": (WebsiteService, "Services", ("name", "slug", "is_active", "sort_order"), None),
    "pricing": (PricingPlan, "Pricing Plans", ("name", "price", "billing_period", "is_active"), None),
    "jobs": (JobOpening, "Job Openings", ("title", "location", "job_type", "is_active"), None),
    "team": (TeamMember, "Team Members", ("name", "designation", "is_active", "sort_order"), None),
    "settings": (WebsiteSettings, "Company Settings", ("company_name", "phone", "email"), None),
    "submissions": (WebsiteSubmission, "Contact Submissions", ("submission_type", "name", "email", "is_read", "created_at"), ("is_read",)),
    "footer-sections": (FooterSection, "Footer Sections", ("title", "section_type", "is_active", "sort_order"), None),
    "footer-links": (FooterLink, "Footer Links", ("label", "section", "url", "is_active", "sort_order"), None),
    "footer-social-links": (FooterSocialLink, "Footer Social Links", ("platform", "url", "is_active", "sort_order"), None),
}


def _config(section):
    if section not in CONFIG:
        raise PermissionDenied
    return CONFIG[section]


def _allowed(request, model, action="view"):
    if not request.user.is_staff or not request.user.has_perm(f"{model._meta.app_label}.{action}_{model._meta.model_name}"):
        raise PermissionDenied


def _form_class(model, fields=None):
    class StyledForm(modelform_factory(model, fields=fields or "__all__")):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            for field in self.fields.values():
                widget = field.widget
                if isinstance(widget, forms.CheckboxInput):
                    widget.attrs["class"] = "oh-switch__checkbox"
                elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                    widget.attrs["class"] = "oh-select oh-select-2 w-100"
                else:
                    widget.attrs["class"] = "oh-input w-100"
                if isinstance(widget, forms.Textarea):
                    widget.attrs.setdefault("rows", 5)
    return StyledForm


@login_required
def cms_list(request, section):
    model, title, columns, _ = _config(section)
    _allowed(request, model)
    objects = model.objects.all()
    rows = []
    for obj in objects:
        cells = []
        for column in columns:
            value = getattr(obj, f"get_{column}_display", lambda: getattr(obj, column, ""))()
            cells.append(value)
        rows.append((obj, cells))
    return render(request, "website/manager/list.html", {
        "section": section, "title": title, "columns": [model._meta.get_field(c).verbose_name for c in columns],
        "rows": rows, "can_add": request.user.has_perm(f"{model._meta.app_label}.add_{model._meta.model_name}"),
        "can_change": request.user.has_perm(f"{model._meta.app_label}.change_{model._meta.model_name}"),
        "can_delete": request.user.has_perm(f"{model._meta.app_label}.delete_{model._meta.model_name}"),
    })


@login_required
def cms_form(request, section, object_id=None):
    model, title, _, limited_fields = _config(section)
    action = "change" if object_id else "add"
    _allowed(request, model, action)
    obj = get_object_or_404(model, pk=object_id) if object_id else None
    Form = _form_class(model, limited_fields)
    form = Form(request.POST or None, request.FILES or None, instance=obj)
    if form.is_valid():
        saved = form.save()
        messages.success(request, f"{saved} saved successfully.")
        return redirect("website-manage-list", section=section)
    return render(request, "website/manager/form.html", {"form": form, "title": title, "section": section, "object": obj})


@login_required
def cms_delete(request, section, object_id):
    model, title, _, _ = _config(section)
    _allowed(request, model, "delete")
    obj = get_object_or_404(model, pk=object_id)
    if request.method == "POST":
        label = str(obj)
        obj.delete()
        messages.success(request, f"{label} deleted successfully.")
        return redirect("website-manage-list", section=section)
    return render(request, "website/manager/delete.html", {"object": obj, "title": title, "section": section})


def _attendance_evidence_queryset():
    """Keep evidence inside the employee/company scope visible to this request."""
    return MobileAttendanceEvidence.objects.select_related("employee").filter(
        employee__in=Employee.objects.all()
    )


@login_required
def attendance_evidence(request):
    _allowed(request, MobileAttendanceEvidence)
    records = _attendance_evidence_queryset()

    employee = request.GET.get("employee", "").strip()
    action = request.GET.get("action", "").strip()
    date_value = request.GET.get("date", "").strip()
    if employee:
        records = records.filter(
            models.Q(employee__employee_first_name__icontains=employee)
            | models.Q(employee__employee_last_name__icontains=employee)
            | models.Q(employee__badge_id__icontains=employee)
            | models.Q(employee__email__icontains=employee)
        )
    if action in {"clock-in", "clock-out"}:
        records = records.filter(action=action)
    if date_value and parse_date(date_value):
        records = records.filter(created_at__date=parse_date(date_value))

    page = Paginator(records, 20).get_page(request.GET.get("page"))
    query = request.GET.copy()
    query.pop("page", None)
    return render(request, "website/manager/attendance_evidence.html", {
        "page": page,
        "query_string": query.urlencode(),
    })


@login_required
def attendance_selfie(request, object_id):
    _allowed(request, MobileAttendanceEvidence)
    evidence = get_object_or_404(_attendance_evidence_queryset(), pk=object_id)
    if not evidence.selfie:
        raise Http404
    try:
        return FileResponse(
            evidence.selfie.open("rb"),
            content_type=getattr(evidence.selfie.file, "content_type", None) or "image/jpeg",
            headers={"Cache-Control": "private, max-age=300", "X-Content-Type-Options": "nosniff"},
        )
    except (FileNotFoundError, OSError, ValueError):
        raise Http404
