from django.contrib import admin, messages
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db import transaction

from .models import (
    Project,
    ProjectStage,
    Task,
    TimeSheet,
    ProjectClosure,
    ProjectCommunicationLog,
)
from .services import check_precompletion, generate_closure_summary, send_completion_notification


def mark_as_completed(modeladmin, request, queryset):
    """Admin action to run the project closure workflow on selected projects."""
    for project in queryset:
        # Step 1: pre‑completion validation
        validation_errors = check_precompletion(project)
        if validation_errors:
            modeladmin.message_user(
                request,
                _(f"Project {project.title} cannot be closed: {validation_errors}"),
                level=messages.ERROR,
            )
            continue

        # Step 2: create or update ProjectClosure atomically
        with transaction.atomic():
            closure, created = ProjectClosure.objects.get_or_create(project=project)
            # Populate delivered modules and statuses
            summary = generate_closure_summary(project, closure)
            closure.delivered_modules = summary.get("modules", {})
            closure.delivery_status = "verified"
            closure.payment_status = "verified"
            closure.approval_status = "approved"
            closure.closed_at = timezone.now()
            closure.save()

        # Step 3: send notification (email channel for now)
        send_completion_notification(project, summary, channels=["email"])

        modeladmin.message_user(
            request,
            _(f"Project {project.title} marked as completed and notification sent."),
            level=messages.SUCCESS,
        )

mark_as_completed.short_description = _("Mark selected projects as completed")


class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "start_date", "end_date", "is_active")
    actions = [mark_as_completed]

admin.site.register(Project, ProjectAdmin)
admin.site.register(ProjectStage)
admin.site.register(Task)
admin.site.register(TimeSheet)
admin.site.register(ProjectClosure)
admin.site.register(ProjectCommunicationLog)
