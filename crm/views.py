from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from crm.models import (
    CRMClient, Inquiry, ClientRequirement, RequirementRevision, 
    RequirementComment, CRMClientAccessLog, Quotation, 
    CRMProjectLink, CRMMeetingLink, CRMCommunication, 
    ClientPayment, CRMActivityLog
)
from crm.forms import (
    InquiryForm, ClientRequirementForm, ClientRequirementAdvancedForm, 
    RequirementCommentForm, CRMMeetingSchedulerForm, QuotationForm, 
    CRMCommunicationForm, ClientPaymentForm, CRMProjectLinkForm, 
    CRMMeetingLinkForm
)
from pms.models import Meetings

@login_required
def inquiry_list(request):
    if not request.user.has_perm("crm.view_inquiry") and not request.user.is_superuser:
        raise PermissionDenied
        
    inquiries = Inquiry.objects.all().select_related("client", "assignee")
    status_groups = {status[0]: [] for status in Inquiry.STATUS_CHOICES}
    for inquiry in inquiries:
        if inquiry.status in status_groups:
            status_groups[inquiry.status].append(inquiry)
            
    return render(request, "crm/inquiry_list.html", {
        "status_groups": status_groups,
        "status_choices": Inquiry.STATUS_CHOICES,
        "all_inquiries": inquiries,
    })


@login_required
def inquiry_create(request):
    if not request.user.has_perm("crm.view_inquiry") and not request.user.is_superuser:
        raise PermissionDenied
        
    form = InquiryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].strip()
        client_name = form.cleaned_data["client_name"].strip()
        company_name = form.cleaned_data["company_name"].strip()
        phone = form.cleaned_data["phone"].strip()

        client_obj, created = CRMClient.objects.get_or_create(
            email=email,
            defaults={
                "name": client_name,
                "company_name": company_name,
                "phone": phone,
                "status": "lead",
            }
        )
        
        if not created:
            updated = False
            if client_name and client_obj.name != client_name:
                client_obj.name = client_name
                updated = True
            if company_name and client_obj.company_name != company_name:
                client_obj.company_name = company_name
                updated = True
            if phone and client_obj.phone != phone:
                client_obj.phone = phone
                updated = True
            if updated:
                client_obj.save()

        inquiry = form.save(commit=False)
        inquiry.client = client_obj
        inquiry.save()

        check_client_status_upgrade(client_obj, inquiry.status)

        CRMActivityLog.objects.create(
            inquiry=inquiry,
            client=client_obj,
            activity_type="inquiry",
            title=_("Inquiry Captured"),
            description=_(f"Service: {inquiry.interested_service}. Requirement: {inquiry.initial_requirement}"),
        )

        messages.success(request, _("Inquiry captured successfully."))
        return redirect("inquiry-list")

    return render(request, "crm/inquiry_form.html", {
        "form": form,
        "title": _("Create Inquiry/Lead"),
    })


@login_required
def inquiry_edit(request, inquiry_id):
    if not request.user.has_perm("crm.view_inquiry") and not request.user.is_superuser:
        raise PermissionDenied
        
    inquiry = get_object_or_404(Inquiry, id=inquiry_id)
    client_obj = inquiry.client
    
    initial_data = {
        "client_name": client_obj.name,
        "company_name": client_obj.company_name,
        "email": client_obj.email,
        "phone": client_obj.phone,
    }
    
    form = InquiryForm(request.POST or None, instance=inquiry, initial=initial_data)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].strip()
        client_name = form.cleaned_data["client_name"].strip()
        company_name = form.cleaned_data["company_name"].strip()
        phone = form.cleaned_data["phone"].strip()

        old_status = inquiry.status
        
        client_obj.name = client_name
        client_obj.company_name = company_name
        client_obj.email = email
        client_obj.phone = phone
        client_obj.save()
        
        inquiry = form.save()
        
        new_status = inquiry.status
        if old_status != new_status:
            check_client_status_upgrade(client_obj, new_status)
            CRMActivityLog.objects.create(
                inquiry=inquiry,
                client=client_obj,
                activity_type="status_change",
                title=_("Status Transition"),
                description=_(f"Quick status change from '{dict(Inquiry.STATUS_CHOICES).get(old_status)}' to '{dict(Inquiry.STATUS_CHOICES).get(new_status)}'"),
            )

        messages.success(request, _("Inquiry updated successfully."))
        return redirect("inquiry-list")

    return render(request, "crm/inquiry_form.html", {
        "form": form,
        "title": _("Edit Inquiry/Lead"),
        "inquiry": inquiry,
    })


@login_required
def inquiry_delete(request, inquiry_id):
    if not request.user.has_perm("crm.view_inquiry") and not request.user.is_superuser:
        raise PermissionDenied
    inquiry = get_object_or_404(Inquiry, id=inquiry_id)
    inquiry.delete()
    messages.success(request, _("Inquiry deleted successfully."))
    return redirect("inquiry-list")


@login_required
def inquiry_update_status(request, inquiry_id):
    if not request.user.has_perm("crm.view_inquiry") and not request.user.is_superuser:
        raise PermissionDenied
    inquiry = get_object_or_404(Inquiry, id=inquiry_id)
    new_status = request.POST.get("status")
    if new_status and new_status in dict(Inquiry.STATUS_CHOICES):
        old_status = inquiry.status
        if old_status != new_status:
            inquiry.status = new_status
            inquiry.save()
            check_client_status_upgrade(inquiry.client, new_status)
            CRMActivityLog.objects.create(
                inquiry=inquiry,
                client=inquiry.client,
                activity_type="status_change",
                title=_("Status Transition"),
                description=_(f"Quick status change from '{dict(Inquiry.STATUS_CHOICES).get(old_status)}' to '{dict(Inquiry.STATUS_CHOICES).get(new_status)}'"),
            )
            messages.success(request, _("Inquiry status updated successfully."))
    return redirect("inquiry-list")


@login_required
def client_timeline(request, client_id):
    if not request.user.has_perm("crm.view_inquiry") and not request.user.is_superuser:
        raise PermissionDenied
    client_obj = get_object_or_404(CRMClient, id=client_id)
    inquiry_id = request.GET.get('inquiry')
    if inquiry_id:
        active_inquiry = get_object_or_404(Inquiry, id=inquiry_id, client=client_obj)
    else:
        active_inquiry = client_obj.inquiries.first()
    logs = CRMActivityLog.objects.filter(client=client_obj).order_by("-created_at")
    
    # Grab active requirements for detail lists
    requirements = ClientRequirement.objects.filter(inquiry__client=client_obj)
    
    # Check if a setup access link was generated/requested
    generated_link = request.session.pop("portal_setup_link", None)
    
    req_form = ClientRequirementForm()
    quote_form = QuotationForm()
    pay_form = ClientPaymentForm()
    comm_form = CRMCommunicationForm()
    project_form = CRMProjectLinkForm()
    meeting_form = CRMMeetingLinkForm()
    
    return render(request, "crm/client_timeline.html", {
        "client": client_obj,
        "active_inquiry": active_inquiry,
        "logs": logs,
        "requirements": requirements,
        "generated_link": generated_link,
        "req_form": req_form,
        "quote_form": quote_form,
        "pay_form": pay_form,
        "comm_form": comm_form,
        "project_form": project_form,
        "meeting_form": meeting_form,
    })


@login_required
def add_requirement(request, inquiry_id):
    inquiry = get_object_or_404(Inquiry, id=inquiry_id)
    form = ClientRequirementForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        req = form.save(commit=False)
        req.inquiry = inquiry
        req.save()
        
        CRMActivityLog.objects.create(
            inquiry=inquiry,
            client=inquiry.client,
            activity_type="requirement",
            title=_("Requirement Discovered"),
            description=_(f"Title: {req.title}\nDescription: {req.description}"),
        )
        messages.success(request, _("Client requirement recorded."))
    return redirect(f"/crm/clients/{inquiry.client.id}/timeline/?inquiry={inquiry.id}")


@login_required
def add_quotation(request, inquiry_id):
    inquiry = get_object_or_404(Inquiry, id=inquiry_id)
    form = QuotationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        quote = form.save(commit=False)
        quote.inquiry = inquiry
        quote.save()
        
        CRMActivityLog.objects.create(
            inquiry=inquiry,
            client=inquiry.client,
            activity_type="quotation",
            title=_("Quotation Generated"),
            description=_(f"Quote #{quote.quote_number}: Amount {quote.amount} ({quote.status})"),
        )
        messages.success(request, _("Quotation saved successfully."))
    return redirect(f"/crm/clients/{inquiry.client.id}/timeline/?inquiry={inquiry.id}")


@login_required
def add_payment(request, inquiry_id):
    inquiry = get_object_or_404(Inquiry, id=inquiry_id)
    form = ClientPaymentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        pay = form.save(commit=False)
        pay.inquiry = inquiry
        pay.save()
        
        CRMActivityLog.objects.create(
            inquiry=inquiry,
            client=inquiry.client,
            activity_type="payment",
            title=_("Payment Logged"),
            description=_(f"Logged amount: {pay.amount}. Reference: {pay.reference_number or 'N/A'} ({pay.status})"),
        )
        messages.success(request, _("Payment logged successfully."))
    return redirect(f"/crm/clients/{inquiry.client.id}/timeline/?inquiry={inquiry.id}")


@login_required
def add_communication(request, inquiry_id):
    inquiry = get_object_or_404(Inquiry, id=inquiry_id)
    form = CRMCommunicationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        comm = form.save(commit=False)
        comm.inquiry = inquiry
        comm.save()
        # Send via appropriate channel using adapters
        if comm.channel == "email":
            from communications.email_adapter import EmailAdapter
            subject = f"Message from {request.user.get_full_name() or request.user.username}"
            recipient = inquiry.client.email
            # Adapter creates CommunicationLog and links EmailLog; we update client reference
            EmailAdapter.send_email(subject, comm.message, [recipient])
            # Associate the generated CommunicationLog with the client
            from communications.models import CommunicationLog
            CommunicationLog.objects.filter(
                channel='email',
                subject=subject,
                body=comm.message,
                client__isnull=True,
            ).update(client=inquiry.client)
        elif comm.channel == "whatsapp":
            from communications.whatsapp_adapter import get_adapter
            adapter = get_adapter()
            phone = inquiry.client.phone
            if phone:
                adapter.send_message(template_name="default", recipient=phone, context={"message": comm.message})
                from communications.models import CommunicationLog
                CommunicationLog.objects.filter(
                    channel='whatsapp',
                    body=comm.message,
                    client__isnull=True,
                ).update(client=inquiry.client)
        # Log to activity timeline
        CRMActivityLog.objects.create(
            inquiry=inquiry,
            client=inquiry.client,
            activity_type="communication",
            title=_(f"Communication via {comm.channel.capitalize()}"),
            description=comm.message,
        )
        messages.success(request, _("Communication touchpoint logged and sent."))
    return redirect(f"/crm/clients/{inquiry.client.id}/timeline/?inquiry={inquiry.id}")


@login_required
def link_project(request, inquiry_id):
    inquiry = get_object_or_404(Inquiry, id=inquiry_id)
    form = CRMProjectLinkForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        link = form.save(commit=False)
        link.inquiry = inquiry
        link.save()
        
        CRMActivityLog.objects.create(
            inquiry=inquiry,
            client=inquiry.client,
            activity_type="project",
            title=_("Project Associated"),
            description=_(f"Associated active project: '{link.project.title}'"),
        )
        messages.success(request, _("Active project linked successfully."))
    return redirect(f"/crm/clients/{inquiry.client.id}/timeline/?inquiry={inquiry.id}")


@login_required
def link_meeting(request, inquiry_id):
    inquiry = get_object_or_404(Inquiry, id=inquiry_id)
    form = CRMMeetingLinkForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        link = form.save(commit=False)
        link.inquiry = inquiry
        link.save()
        
        CRMActivityLog.objects.create(
            inquiry=inquiry,
            client=inquiry.client,
            activity_type="meeting",
            title=_("Meeting Associated"),
            description=_(f"Linked client meeting: '{link.meeting.title}'"),
        )
        messages.success(request, _("Meeting associated successfully."))
    return redirect(f"/crm/clients/{inquiry.client.id}/timeline/?inquiry={inquiry.id}")


# Helper function to upgrade CRMClient status based on inquiry status
from django.db import models
from crm.models import InquiryNote

# Helper function to upgrade CRMClient status based on inquiry status
def check_client_status_upgrade(client_obj, inquiry_status):
    confirmed_stages = ["qualified", "confirmed_client", "active_project", "payment", "project_delivery"]
    long_term_stages = ["successful_completion", "long_term_client"]

    if inquiry_status in long_term_stages:
        if client_obj.status != "long_term":
            client_obj.status = "long_term"
            client_obj.save()
    elif inquiry_status in confirmed_stages:
        if client_obj.status not in ["confirmed", "long_term"]:
            client_obj.status = "confirmed"
            client_obj.save()

# View to add note to an inquiry
@login_required
def add_inquiry_note(request, inquiry_id):
    inquiry = get_object_or_404(Inquiry, id=inquiry_id)
    if request.method == "POST":
        form = InquiryNoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.inquiry = inquiry
            note.author = request.user
            note.save()
            CRMActivityLog.objects.create(
                inquiry=inquiry,
                client=inquiry.client,
                activity_type="note",
                title=_("Note added"),
                description=note.content,
            )
            messages.success(request, _("Note added successfully."))
            return redirect(f"/crm/clients/{inquiry.client.id}/timeline/?inquiry={inquiry.id}")
    else:
        form = InquiryNoteForm()
    return render(request, "crm/inquiry_note_form.html", {"form": form, "inquiry": inquiry})

# Updated inquiry_create to generate reference_number for new inquiries
@login_required
def inquiry_create(request):
    if not request.user.has_perm("crm.view_inquiry") and not request.user.is_superuser:
        raise PermissionDenied

    form = InquiryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].strip()
        client_name = form.cleaned_data["client_name"].strip()
        company_name = form.cleaned_data["company_name"].strip()
        phone = form.cleaned_data["phone"].strip()

        client_obj, created = CRMClient.objects.get_or_create(
            email=email,
            defaults={
                "name": client_name,
                "company_name": company_name,
                "phone": phone,
                "status": "lead",
            }
        )

        if not created:
            updated = False
            if client_name and client_obj.name != client_name:
                client_obj.name = client_name
                updated = True
            if company_name and client_obj.company_name != company_name:
                client_obj.company_name = company_name
                updated = True
            if phone and client_obj.phone != phone:
                client_obj.phone = phone
                updated = True
            if updated:
                client_obj.save()

        inquiry = form.save(commit=False)
        inquiry.client = client_obj
        inquiry.save()
        # Generate reference number for new inquiries if not set
        if not inquiry.reference_number:
            inquiry.reference_number = f"INV-{inquiry.id}"
            inquiry.save(update_fields=["reference_number"])

        check_client_status_upgrade(client_obj, inquiry.status)

        CRMActivityLog.objects.create(
            inquiry=inquiry,
            client=client_obj,
            activity_type="inquiry",
            title=_("Inquiry Captured"),
            description=_(f"Service: {inquiry.interested_service}. Requirement: {inquiry.initial_requirement}"),
        )

        messages.success(request, _("Inquiry captured successfully."))
        return redirect("inquiry-list")

    return render(request, "crm/inquiry_form.html", {"form": form, "title": _("Create Inquiry/Lead"),})
    confirmed_stages = ["confirmed_client", "active_project", "payment", "project_delivery"]
    long_term_stages = ["successful_completion", "long_term_client"]
    
    if inquiry_status in long_term_stages:
        if client_obj.status != "long_term":
            client_obj.status = "long_term"
            client_obj.save()
    elif inquiry_status in confirmed_stages:
        if client_obj.status != "confirmed" and client_obj.status != "long_term":
            client_obj.status = "confirmed"
            client_obj.save()


# ---------------------------------------------------------------------------
# Advanced Client Requirement Management Views
# ---------------------------------------------------------------------------

@login_required
def requirement_create(request, inquiry_id):
    if not request.user.has_perm("crm.view_inquiry") and not request.user.is_superuser:
        raise PermissionDenied
    inquiry = get_object_or_404(Inquiry, id=inquiry_id)
    form = ClientRequirementAdvancedForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        req = form.save(commit=False)
        req.inquiry = inquiry
        req.save()
        form.save_m2m() # Save team assignments
        
        # Log to timeline
        CRMActivityLog.objects.create(
            inquiry=inquiry,
            client=inquiry.client,
            activity_type="requirement",
            title=_("Requirement Base Created"),
            description=_(f"Title: {req.title}\nPriority: {req.priority}\nRequested Modules: {req.modules_requested or 'None'}"),
        )
        messages.success(request, _("Detailed client requirement specification created."))
        return redirect(f"/crm/clients/{inquiry.client.id}/timeline/?inquiry={inquiry.id}")
        
    return render(request, "crm/requirement_form.html", {
        "form": form,
        "title": _("Create Specification Details"),
        "inquiry": inquiry,
    })


@login_required
def requirement_edit(request, req_id):
    if not request.user.has_perm("crm.view_inquiry") and not request.user.is_superuser:
        raise PermissionDenied
    req = get_object_or_404(ClientRequirement, id=req_id)
    form = ClientRequirementAdvancedForm(request.POST or None, request.FILES or None, instance=req)
    if request.method == "POST" and form.is_valid():
        # Audit requirement revision using original database state
        original_req = ClientRequirement.objects.get(id=req.id)
        RequirementRevision.objects.create(
            requirement=req,
            revision_number=original_req.revision_number,
            title=original_req.title,
            description=original_req.description,
            modules_requested=original_req.modules_requested,
            priority=original_req.priority,
            attachment=original_req.attachment,
            updated_by=request.user,
        )
        
        # Update requirement specification
        updated_req = form.save(commit=False)
        updated_req.revision_number += 1
        updated_req.save()
        form.save_m2m()
        
        # Log timeline revision history
        CRMActivityLog.objects.create(
            inquiry=req.inquiry,
            client=req.inquiry.client,
            activity_type="status_change",
            title=_("Requirement Revised"),
            description=_(f"Specification revised to revision #{updated_req.revision_number} by {request.user.username}."),
        )
        messages.success(request, _("Requirement specifications updated and revision logged."))
        return redirect("crm-requirement-detail", req_id=req.id)
        
    return render(request, "crm/requirement_form.html", {
        "form": form,
        "title": _("Edit Specifications"),
        "inquiry": req.inquiry,
    })


@login_required
def requirement_detail(request, req_id):
    # Portal authorization vs Admin validation check
    req = get_object_or_404(ClientRequirement, id=req_id)
    is_client = hasattr(request.user, "crm_client_profile")
    if is_client and request.user.crm_client_profile != req.inquiry.client:
        raise PermissionDenied
    if not is_client and not request.user.has_perm("crm.view_inquiry") and not request.user.is_superuser:
        raise PermissionDenied
        
    comments = req.comments.all().select_related("author").order_by("created_at")
    revisions = req.revisions.all().select_related("updated_by").order_by("-revision_number")
    comment_form = RequirementCommentForm()
    
    return render(request, "crm/requirement_detail.html", {
        "requirement": req,
        "comments": comments,
        "revisions": revisions,
        "comment_form": comment_form,
    })


@login_required
def add_requirement_comment(request, req_id):
    req = get_object_or_404(ClientRequirement, id=req_id)
    is_client = hasattr(request.user, "crm_client_profile")
    if is_client and request.user.crm_client_profile != req.inquiry.client:
        raise PermissionDenied
    if not is_client and not request.user.has_perm("crm.view_inquiry") and not request.user.is_superuser:
        raise PermissionDenied
        
    form = RequirementCommentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        comment = form.save(commit=False)
        comment.requirement = req
        comment.author = request.user
        comment.save()
        
        # Log to activity timeline
        CRMActivityLog.objects.create(
            inquiry=req.inquiry,
            client=req.inquiry.client,
            activity_type="communication",
            title=_("Requirement Comment Added"),
            description=_(f"{request.user.username} commented: {comment.comment}"),
        )
        messages.success(request, _("Comment added to discussion thread."))
    return redirect("crm-requirement-detail", req_id=req.id)


# ---------------------------------------------------------------------------
# Client Scheduler Views
# ---------------------------------------------------------------------------

@login_required
def schedule_client_meeting(request, inquiry_id):
    if not request.user.has_perm("crm.view_inquiry") and not request.user.is_superuser:
        raise PermissionDenied
    inquiry = get_object_or_404(Inquiry, id=inquiry_id)
    form = CRMMeetingSchedulerForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        # Setup meetings object
        meeting = form.save(commit=False)
        meeting.meeting_type = "external" # client meeting
        meeting.save()
        form.save_m2m() # Save manager/employees
        
        # Link meeting with crm link
        CRMMeetingLink.objects.create(inquiry=inquiry, meeting=meeting)
        
        # Log scheduler event
        CRMActivityLog.objects.create(
            inquiry=inquiry,
            client=inquiry.client,
            activity_type="meeting",
            title=_("Meeting Scheduled"),
            description=_(f"External call: '{meeting.title}' scheduled for {meeting.date} via {meeting.provider.capitalize()}."),
        )
        messages.success(request, _("Client meeting scheduled successfully."))
        return redirect(f"/crm/clients/{inquiry.client.id}/timeline/?inquiry={inquiry.id}")
        
    return render(request, "crm/schedule_form.html", {
        "form": form,
        "inquiry": inquiry,
    })


# ---------------------------------------------------------------------------
# One-click Secure Client Portal Access Views
# ---------------------------------------------------------------------------

@login_required
def update_portal_access(request, client_id, action_type):
    if not request.user.has_perm("crm.view_inquiry") and not request.user.is_superuser:
        raise PermissionDenied
    client_obj = get_object_or_404(CRMClient, id=client_id)
    
    if action_type == "grant":
        if not client_obj.portal_user:
            # Create portal user
            user = User.objects.create_user(
                username=client_obj.email,
                email=client_obj.email,
            )
            client_obj.portal_user = user
            
        client_obj.is_portal_active = True
        client_obj.portal_user.is_active = True
        client_obj.portal_user.save()
        client_obj.save()
        
        # Log access action
        CRMClientAccessLog.objects.create(
            client=client_obj,
            action="granted",
            performed_by=request.user,
            ip_address=request.META.get("REMOTE_ADDR")
        )
        
        # Generate secure one-time access token link
        token = default_token_generator.make_token(client_obj.portal_user)
        uid = urlsafe_base64_encode(force_bytes(client_obj.portal_user.pk))
        portal_setup_link = request.build_absolute_uri(
            redirect("crm-client-token-login", uidb64=uid, token=token).url
        )
        
        request.session["portal_setup_link"] = portal_setup_link
        messages.success(request, _("Access credentials configured. Setup link generated."))
        
    elif action_type == "revoke":
        if client_obj.portal_user:
            client_obj.is_portal_active = False
            client_obj.portal_user.is_active = False
            client_obj.portal_user.save()
            client_obj.save()
            
            CRMClientAccessLog.objects.create(
                client=client_obj,
                action="revoked",
                performed_by=request.user,
                ip_address=request.META.get("REMOTE_ADDR")
            )
            messages.success(request, _("Client portal access revoked successfully."))
            
    return redirect("client-timeline", client_id=client_obj.id)


def client_token_login(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        # Validate that the client profile is actually active
        client_profile = getattr(user, "crm_client_profile", None)
        if client_profile and client_profile.is_portal_active:
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            
            # Log successful login activity
            CRMClientAccessLog.objects.create(
                client=client_profile,
                action="login",
                performed_by=user,
                ip_address=request.META.get("REMOTE_ADDR")
            )
            messages.success(request, _("Welcome to your client workspace!"))
            return redirect("crm-client-portal-dashboard")

    messages.error(request, _("This one-click access link is invalid, expired, or access has been revoked."))
    return redirect("/login/")


@login_required
def client_portal_dashboard(request):
    # Enforce restricted dashboard authorization
    is_client = hasattr(request.user, "crm_client_profile")
    if not is_client:
        messages.error(request, _("Access denied. Portal restricted to confirmed client workspace accounts."))
        return redirect("/login/")
        
    client_obj = request.user.crm_client_profile
    if not client_obj.is_portal_active:
        raise PermissionDenied
        
    inquiries = client_obj.inquiries.all()
    active_inquiry = inquiries.exclude(
        status__in=["closed", "archived", "successful_completion"]
    ).first() or inquiries.first()
    requirements = ClientRequirement.objects.filter(inquiry__client=client_obj).order_by("-created_at")
    payments = ClientPayment.objects.filter(inquiry__client=client_obj).order_by("-payment_date")
    logs = CRMActivityLog.objects.filter(client=client_obj).order_by("-created_at")
    
    # Fetch linked projects
    project_links = CRMProjectLink.objects.filter(inquiry__client=client_obj).select_related("project")
    projects = [link.project for link in project_links]
    
    return render(request, "crm/portal_dashboard.html", {
        "client": client_obj,
        "active_inquiry": active_inquiry,
        "requirements": requirements,
        "payments": payments,
        "projects": projects,
        "logs": logs,
    })


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
