# project/services.py
"""Service layer for project closure workflow.
This module provides helper functions used by the admin action to:
1. Validate that a project can be closed (`check_precompletion`).
2. Build a summary of delivered modules and payment information (`generate_closure_summary`).
3. Send a completion notification via configured channels (`send_completion_notification`).
"""

import hashlib
import json
from typing import List, Dict, Any, Optional

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# Import models – adjust paths if apps are named differently.
# Assuming the models live in the same app (project) as this file.
from .models import Project, ProjectClosure, ProjectCommunicationLog

# Placeholder imports for cross‑app models. Update if actual app/module names differ.
try:
    from task.models import Task
except ImportError:
    Task = None  # type: ignore
try:
    from quotations.models import Quotation, QuotationPayment, QuotationPaymentSchedule
except ImportError:
    Quotation = QuotationPayment = QuotationPaymentSchedule = None  # type: ignore


def _hash_summary(content: str) -> str:
    """Return a SHA‑256 hex digest of the given content.
    Used to deduplicate communication logs.
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def check_precompletion(project: Project) -> Optional[str]:
    """Validate that a project meets all pre‑completion criteria.

    Returns ``None`` if everything is OK, otherwise a string describing the problem.
    """
    # 1. All tasks must be completed.
    if Task is None:
        return _("Task model not available for validation.")
    incomplete_tasks = project.task_set.exclude(status=Task.STATUS_COMPLETED if hasattr(Task, "STATUS_COMPLETED") else "completed")
    if incomplete_tasks.exists():
        titles = ", ".join(incomplete_tasks.values_list("title", flat=True)[:5])
        return _(f"Project has incomplete tasks: {titles}")

    # 2. Payments must be fully settled.
    if Quotation and QuotationPaymentSchedule:
        quotations = Quotation.objects.filter(project=project)
        for q in quotations:
            unpaid = QuotationPaymentSchedule.objects.filter(
                quotation=q, status=QuotationPaymentSchedule.STATUS_PENDING
            ).exists()
            if unpaid:
                return _("There are unpaid payment schedules for this project's quotation.")
    # 3. Internal approvals – placeholder.
    return None


def generate_closure_summary(project: Project, closure: ProjectClosure) -> Dict[str, Any]:
    """Build a summary dict used for email rendering and logging.

    The returned dict contains at least ``modules`` (a list of delivered module titles)
    and ``summary`` (rendered HTML string).
    """
    modules = list(project.task_set.filter(status="completed").values_list("title", flat=True))
    delivered_modules = {"modules": modules}

    payment_summary = {}
    if Quotation:
        quotations = Quotation.objects.filter(project=project)
        total = sum(q.details.get("total", 0) for q in quotations)
        payment_summary = {"total": total}

    context = {
        "project": project,
        "modules": modules,
        "payment_summary": payment_summary,
        "support_contact": getattr(settings, "SUPPORT_EMAIL", "support@example.com"),
        "project_url": getattr(settings, "SITE_URL", "http://localhost:8000") + f"/project/{project.id}/",
    }
    try:
        summary_html = render_to_string("project/closure_email.html", context)
    except Exception:
        summary_html = (
            f"<p>Project <strong>{project.title}</strong> has been completed.</p>"
            f"<p>Delivered modules: {', '.join(modules) or 'None'}.</p>"
        )

    closure.delivered_modules = delivered_modules
    closure.save(update_fields=["delivered_modules"])

    return {"modules": delivered_modules, "summary": summary_html, "context": context}


def send_completion_notification(project: Project, summary: Dict[str, Any], channels: List[str] = ["email"]):
    """Send completion notifications via the requested channels.

    Currently supports only ``email``. Additional channels can be added later.
    """
    summary_html = summary.get("summary", "")
    msg_hash = _hash_summary(summary_html)
    for channel in channels:
        if channel == "email":
            subject = _(f"Project {project.title} – Completion Notification")
            from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com")
            recipient_list = []
            if hasattr(project, "client") and getattr(project, "client", None):
                recipient_list = [project.client.email]
            if not recipient_list:
                recipient_list = [getattr(settings, "ADMIN_EMAIL", from_email)]
            send_mail(subject, "", from_email, recipient_list, html_message=summary_html)
            ProjectCommunicationLog.objects.create(
                project=project,
                channel="email",
                summary_hash=msg_hash,
                status="sent",
            )
        else:
            ProjectCommunicationLog.objects.create(
                project=project,
                channel=channel,
                summary_hash=msg_hash,
                status="pending",
            )

# End of services module
