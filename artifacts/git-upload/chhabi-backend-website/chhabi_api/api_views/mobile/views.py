from django.apps import apps
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from django.core.exceptions import FieldDoesNotExist
from django.db import models
import base64
import uuid
from datetime import timedelta
from django.core.files.base import ContentFile
from chhabi_api.models import MobileAttendanceEvidence


def employee_for(user):
    return getattr(user, "employee_get", None)


def company_for(employee):
    return getattr(getattr(employee, "employee_work_info", None), "company_id", None)


class BootstrapAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        employee = employee_for(request.user)
        work_info = getattr(employee, "employee_work_info", None)
        company = company_for(employee)
        profile = {
            "id": getattr(employee, "id", None),
            "username": request.user.username,
            "full_name": employee.get_full_name() if employee else request.user.get_full_name(),
            "email": getattr(employee, "email", request.user.email),
            "phone": getattr(employee, "phone", ""),
            "profile": request.build_absolute_uri(employee.employee_profile.url)
            if employee and employee.employee_profile else None,
            "company": getattr(company, "company", None),
            "company_id": getattr(company, "id", None),
            "department": str(getattr(work_info, "department_id", "") or ""),
            "job_position": str(getattr(work_info, "job_position_id", "") or ""),
            "badge_id": getattr(employee, "badge_id", None),
        }
        permissions = sorted(request.user.get_all_permissions())
        modules = {
            "employees": request.user.is_superuser or request.user.has_perm("employee.view_employee"),
            "attendance": True,
            "leave": True,
            "payroll": True,
            "recruitment": request.user.is_superuser or request.user.has_perm("recruitment.view_recruitment"),
            "assets": request.user.is_superuser or request.user.has_perm("asset.view_asset"),
            "meetings": True,
            "reports": request.user.is_superuser or any(p.startswith(("employee.view_", "attendance.view_", "leave.view_", "payroll.view_")) for p in permissions),
            "documents": True,
            "notifications": True,
        }
        return Response({"profile": profile, "permissions": permissions, "modules": modules})


class DashboardAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        employee = employee_for(request.user)
        today = timezone.localdate()
        stats = {"employees": 0, "present_today": 0, "pending_leaves": 0, "upcoming_meetings": 0, "notifications": 0}
        attendance_trend = []
        if apps.is_installed("employee"):
            Employee = apps.get_model("employee", "Employee")
            stats["employees"] = Employee.objects.filter(is_active=True).count()
        if apps.is_installed("attendance"):
            Attendance = apps.get_model("attendance", "Attendance")
            stats["present_today"] = Attendance.objects.filter(attendance_date=today).count()
            start = today - timedelta(days=6)
            daily_counts = {
                row["attendance_date"]: row["total"]
                for row in Attendance.objects.filter(
                    attendance_date__range=(start, today)
                ).values("attendance_date").annotate(total=models.Count("id"))
            }
            attendance_trend = [
                {
                    "date": day.isoformat(),
                    "label": day.strftime("%a")[0],
                    "present": daily_counts.get(day, 0),
                }
                for day in (start + timedelta(days=offset) for offset in range(7))
            ]
        if apps.is_installed("leave"):
            LeaveRequest = apps.get_model("leave", "LeaveRequest")
            leaves = LeaveRequest.objects.filter(status="requested")
            if not request.user.is_superuser and employee:
                leaves = leaves.filter(employee_id=employee)
            stats["pending_leaves"] = leaves.count()
        if apps.is_installed("pms"):
            Meetings = apps.get_model("pms", "Meetings")
            meetings = Meetings.objects.filter(date__gte=timezone.now(), is_active=True)
            if not request.user.is_superuser and employee:
                meetings = meetings.filter(employee_id=employee) | meetings.filter(manager=employee)
            stats["upcoming_meetings"] = meetings.distinct().count()
        try:
            stats["notifications"] = request.user.notifications.unread().count()
        except Exception:
            pass
        attendance_rate = round(
            (stats["present_today"] / stats["employees"] * 100), 1
        ) if stats["employees"] else 0
        return Response({
            "date": today,
            "stats": stats,
            "attendance_rate": attendance_rate,
            "attendance_trend": attendance_trend,
        })


class RecruitmentAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        if not (request.user.is_superuser or request.user.has_perm("recruitment.view_recruitment")):
            return Response({"detail": "Permission denied"}, status=403)
        Recruitment = apps.get_model("recruitment", "Recruitment")
        rows = Recruitment.objects.order_by("-id")[:100]
        return Response([
            {
                "id": row.id,
                "title": str(row),
                "status": getattr(row, "status", None),
                "start_date": getattr(row, "start_date", None),
                "end_date": getattr(row, "end_date", None),
            }
            for row in rows
        ])


# Explicit allow-list for native mobile CRUD. Nothing outside this registry can
# be queried by the generic endpoints.
MOBILE_MODELS = {
    "companies": "base.Company", "departments": "base.Department",
    "job-positions": "base.JobPosition", "job-roles": "base.JobRole",
    "work-types": "base.WorkType", "shifts": "base.EmployeeShift",
    "announcements": "base.Announcement", "employees": "employee.Employee",
    "employee-notes": "employee.EmployeeNote", "policies": "employee.Policy",
    "disciplinary-actions": "employee.DisciplinaryAction",
    "recruitments": "recruitment.Recruitment", "candidates": "recruitment.Candidate",
    "interviews": "recruitment.InterviewSchedule", "stages": "recruitment.Stage",
    "skills": "recruitment.Skill", "skill-zones": "recruitment.SkillZone",
    "onboarding-stages": "onboarding.OnboardingStage",
    "onboarding-tasks": "onboarding.OnboardingTask",
    "onboarding-candidates": "onboarding.OnboardingCandidate",
    "attendances": "attendance.Attendance", "attendance-activities": "attendance.AttendanceActivity",
    "overtime": "attendance.AttendanceOverTime", "late-early": "attendance.AttendanceLateComeEarlyOut",
    "work-records": "attendance.WorkRecords", "leave-types": "leave.LeaveType",
    "leave-requests": "leave.LeaveRequest", "leave-allocations": "leave.LeaveAllocationRequest",
    "holidays": "leave.Holiday", "company-leaves": "leave.CompanyLeave",
    "contracts": "payroll.Contract", "allowances": "payroll.Allowance",
    "deductions": "payroll.Deduction", "payslips": "payroll.Payslip",
    "loans": "payroll.LoanAccount", "reimbursements": "payroll.Reimbursement",
    "periods": "pms.Period", "objectives": "pms.Objective",
    "employee-objectives": "pms.EmployeeObjective", "key-results": "pms.KeyResult",
    "feedback": "pms.Feedback", "question-templates": "pms.QuestionTemplate",
    "meetings": "pms.Meetings", "meeting-notes": "pms.MeetingNote",
    "offboarding": "offboarding.Offboarding", "offboarding-stages": "offboarding.OffboardingStage",
    "resignations": "offboarding.ResignationLetter", "offboarding-tasks": "offboarding.OffboardingTask",
    "assets": "asset.Asset", "asset-categories": "asset.AssetCategory",
    "asset-batches": "asset.AssetLot", "asset-requests": "asset.AssetRequest",
    "tickets": "helpdesk.Ticket", "ticket-types": "helpdesk.TicketType",
    "faqs": "helpdesk.FAQ", "faq-categories": "helpdesk.FAQCategory",
    "projects": "project.Project", "project-stages": "project.ProjectStage",
    "tasks": "project.Task", "timesheets": "project.TimeSheet",
}

MODULE_GROUPS = {
    "base": ("Organisation", "🏢"), "employee": ("Employees", "👥"),
    "recruitment": ("Recruitment", "🎯"), "onboarding": ("Onboarding", "🚀"),
    "attendance": ("Attendance", "🕐"), "leave": ("Leave", "🏖️"),
    "payroll": ("Payroll", "💰"), "pms": ("Performance & Meetings", "📈"),
    "offboarding": ("Offboarding", "👋"), "asset": ("Assets", "💻"),
    "helpdesk": ("Helpdesk", "🎫"), "project": ("Projects", "📋"),
}


class MobileModulesAPIView(APIView):
    """Return only installed modules the signed-in user may actually view."""
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        groups = {}
        for key in MOBILE_MODELS:
            try:
                model = mobile_model(key)
            except LookupError:
                continue
            if not model or not can(request.user, "view", model):
                continue
            app_label = model._meta.app_label
            title, icon = MODULE_GROUPS.get(
                app_label, (apps.get_app_config(app_label).verbose_name, "📁")
            )
            group = groups.setdefault(app_label, {
                "key": app_label, "title": str(title), "icon": icon, "modules": []
            })
            group["modules"].append({
                "key": key,
                "title": str(model._meta.verbose_name_plural).title(),
                "icon": "📄",
                "endpoint": f"/mobile/records/{key}/",
            })
        return Response({"sections": list(groups.values())})


class SecureAttendanceAPIView(APIView):
    """Consent-driven mobile attendance: OS biometric result, GPS and visible selfie."""
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        action = request.data.get("action")
        if action not in ("clock-in", "clock-out"):
            return Response({"detail": "Invalid attendance action"}, status=400)
        if request.data.get("biometric_verified") is not True:
            return Response({"detail": "Device biometric verification is required"}, status=400)
        latitude, longitude = request.data.get("latitude"), request.data.get("longitude")
        selfie = request.data.get("selfie")
        if latitude is None or longitude is None or not selfie:
            return Response({"detail": "Live location and front-camera selfie are required"}, status=400)
        try:
            encoded = selfie.split(",", 1)[-1]
            image = ContentFile(base64.b64decode(encoded), name=f"{uuid.uuid4().hex}.jpg")
        except Exception:
            return Response({"detail": "Invalid selfie image"}, status=400)

        from chhabi_api.api_views.attendance.views import ClockInAPIView, ClockOutAPIView
        response = (ClockInAPIView() if action == "clock-in" else ClockOutAPIView()).post(request)
        if response.status_code == 200:
            MobileAttendanceEvidence.objects.create(
                employee=employee_for(request.user), action=action,
                latitude=latitude, longitude=longitude,
                accuracy=request.data.get("accuracy"), biometric_verified=True, selfie=image,
            )
        return response


def mobile_model(key):
    label = MOBILE_MODELS.get(key)
    if not label:
        return None
    app_label, model_name = label.split(".")
    return apps.get_model(app_label, model_name)


def can(user, action, model):
    return user.is_superuser or user.has_perm(
        f"{model._meta.app_label}.{action}_{model._meta.model_name}"
    )


def serialize_record(obj):
    result = {"id": obj.pk, "display": str(obj)}
    for field in obj._meta.concrete_fields:
        if field.primary_key or isinstance(field, (models.BinaryField, models.FileField)):
            continue
        value = getattr(obj, field.name, None)
        if field.is_relation:
            result[field.name] = getattr(value, "pk", None)
            result[f"{field.name}_display"] = str(value) if value else None
        else:
            result[field.name] = value
    return result


def field_schema(field):
    kind = "text"
    if field.is_relation:
        kind = "relation"
    elif isinstance(field, models.BooleanField):
        kind = "boolean"
    elif isinstance(field, (models.DateField, models.DateTimeField)):
        kind = "datetime" if isinstance(field, models.DateTimeField) else "date"
    elif isinstance(field, (models.IntegerField, models.FloatField, models.DecimalField)):
        kind = "number"
    choices = [{"value": value, "label": str(label)} for value, label in (field.choices or [])]
    options = []
    if field.is_relation and getattr(field, "related_model", None):
        try:
            options = [{"value": row.pk, "label": str(row)} for row in field.related_model._default_manager.all()[:200]]
        except Exception:
            pass
    return {"name": field.name, "label": str(field.verbose_name).title(), "type": kind,
            "required": not field.blank and not field.null and not field.has_default(),
            "choices": choices, "options": options}


def editable_fields(model):
    return [field for field in model._meta.concrete_fields
            if field.editable and not field.primary_key and not isinstance(field, (models.FileField, models.BinaryField))]


def apply_payload(instance, payload, fields):
    for field in fields:
        if field.name not in payload:
            continue
        value = payload[field.name]
        if value == "" and field.null:
            value = None
        if field.is_relation:
            setattr(instance, field.attname, value or None)
        else:
            setattr(instance, field.name, value)
    instance.full_clean()
    instance.save()
    return instance


class MobileRecordsAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, key):
        model = mobile_model(key)
        if not model:
            return Response({"detail": "Unknown mobile module"}, status=404)
        if not can(request.user, "view", model):
            return Response({"detail": "Permission denied"}, status=403)
        queryset = model._default_manager.all().order_by("-pk")[:200]
        fields = editable_fields(model)
        return Response({"key": key, "title": str(model._meta.verbose_name_plural).title(),
                         "can_add": can(request.user, "add", model),
                         "can_change": can(request.user, "change", model),
                         "can_delete": can(request.user, "delete", model),
                         "schema": [field_schema(field) for field in fields],
                         "results": [serialize_record(row) for row in queryset]})

    def post(self, request, key):
        model = mobile_model(key)
        if not model or not can(request.user, "add", model):
            return Response({"detail": "Permission denied"}, status=403)
        try:
            instance = apply_payload(model(), request.data, editable_fields(model))
            return Response(serialize_record(instance), status=status.HTTP_201_CREATED)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=400)


class MobileRecordDetailAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def patch(self, request, key, pk):
        model = mobile_model(key)
        if not model or not can(request.user, "change", model):
            return Response({"detail": "Permission denied"}, status=403)
        instance = model._default_manager.filter(pk=pk).first()
        if not instance:
            return Response({"detail": "Record not found"}, status=404)
        try:
            return Response(serialize_record(apply_payload(instance, request.data, editable_fields(model))))
        except Exception as exc:
            return Response({"detail": str(exc)}, status=400)

    def delete(self, request, key, pk):
        model = mobile_model(key)
        if not model or not can(request.user, "delete", model):
            return Response({"detail": "Permission denied"}, status=403)
        instance = model._default_manager.filter(pk=pk).first()
        if not instance:
            return Response({"detail": "Record not found"}, status=404)
        instance.delete()
        return Response(status=204)
