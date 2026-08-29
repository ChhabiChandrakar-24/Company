import os

filepath = 'crm/views.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

new_views = """

# --- Phase 8: Missing Modules ---

from django.db.models import Sum, Count
from django.utils import timezone
from crm.models import Company, Deal, CRMTask
from crm.forms import CompanyForm, DealForm, CRMTaskForm

@login_required
def crm_dashboard(request):
    if not request.user.has_perm("crm.view_inquiry") and not request.user.is_superuser:
        raise PermissionDenied
        
    lead_count = Inquiry.objects.exclude(status__in=["won", "lost", "long_term_client"]).count()
    active_deals = Deal.objects.exclude(stage__in=["won", "lost"]).count()
    pipeline_value = Deal.objects.exclude(stage__in=["won", "lost"]).aggregate(total=Sum('amount'))['total'] or 0.00
    upcoming_tasks = CRMTask.objects.filter(is_completed=False, due_date__gte=timezone.now()).count()
    recent_activities = CRMActivityLog.objects.all()[:10]
    
    pipeline_summary = Deal.objects.values('stage').annotate(count=Count('id')).order_by('stage')
    
    return render(request, "crm/dashboard.html", {
        "lead_count": lead_count,
        "active_deals": active_deals,
        "pipeline_value": pipeline_value,
        "upcoming_tasks": upcoming_tasks,
        "recent_activities": recent_activities,
        "pipeline_summary": pipeline_summary,
    })

@login_required
def company_list(request):
    if not request.user.has_perm("crm.view_inquiry") and not request.user.is_superuser:
        raise PermissionDenied
    companies = Company.objects.all()
    return render(request, "crm/company_list.html", {"companies": companies})

@login_required
def company_create(request):
    if not request.user.has_perm("crm.change_inquiry") and not request.user.is_superuser:
        raise PermissionDenied
    form = CompanyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Company created successfully."))
        return redirect("company-list")
    return render(request, "crm/company_form.html", {"form": form})

@login_required
def company_detail(request, company_id):
    if not request.user.has_perm("crm.view_inquiry") and not request.user.is_superuser:
        raise PermissionDenied
    company = get_object_or_404(Company, id=company_id)
    return render(request, "crm/company_detail.html", {"company": company})

@login_required
def deal_pipeline(request):
    if not request.user.has_perm("crm.view_inquiry") and not request.user.is_superuser:
        raise PermissionDenied
    deals = Deal.objects.all()
    stages = [choice[0] for choice in Deal.STAGE_CHOICES]
    return render(request, "crm/deal_pipeline.html", {"deals": deals, "stages": stages, "stage_choices": Deal.STAGE_CHOICES})

@login_required
def convert_to_deal(request, inquiry_id):
    if not request.user.has_perm("crm.change_inquiry") and not request.user.is_superuser:
        raise PermissionDenied
    inquiry = get_object_or_404(Inquiry, id=inquiry_id)
    
    # Try to get or create deal
    deal, created = Deal.objects.get_or_create(
        inquiry=inquiry,
        defaults={
            "title": f"Deal for {inquiry.client.name}",
            "amount": 0,
            "owner": inquiry.assignee
        }
    )
    if created:
        CRMActivityLog.objects.create(
            inquiry=inquiry,
            client=inquiry.client,
            activity_type="status_change",
            title=_("Lead Converted to Deal"),
            description=_("A new deal has been instantiated for this lead."),
        )
        messages.success(request, _("Lead converted to Deal successfully."))
    else:
        messages.info(request, _("Deal already exists for this lead."))
    return redirect("deal-pipeline")

@login_required
def add_crm_task(request, inquiry_id):
    if not request.user.has_perm("crm.change_inquiry") and not request.user.is_superuser:
        raise PermissionDenied
    inquiry = get_object_or_404(Inquiry, id=inquiry_id)
    form = CRMTaskForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        task = form.save(commit=False)
        task.inquiry = inquiry
        task.client = inquiry.client
        if hasattr(inquiry, 'deal'):
            task.deal = inquiry.deal
        task.save()
        CRMActivityLog.objects.create(
            inquiry=inquiry,
            client=inquiry.client,
            activity_type="communication",
            title=_(f"{task.get_activity_type_display()} Scheduled"),
            description=_(f"{task.title} (Due: {task.due_date})"),
        )
        messages.success(request, _("Task/Follow-up added."))
        return redirect(f"/crm/clients/{inquiry.client.id}/timeline/?inquiry={inquiry.id}")
    
    return render(request, "crm/task_form.html", {"form": form, "inquiry": inquiry})
"""
content += new_views

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
