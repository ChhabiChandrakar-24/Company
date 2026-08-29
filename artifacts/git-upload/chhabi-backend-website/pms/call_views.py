import json
from datetime import timedelta

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import FileResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from .models import (
    MeetingCaption,
    MeetingMessage,
    MeetingNote,
    MeetingProviderConfig,
    MeetingRecording,
    MeetingSignal,
    Meetings,
)
from .meeting_providers import provision_external_meeting


def _can_access(user, meeting):
    if user.is_superuser or user.has_perm("pms.manage_meeting_integrations"):
        return True
    employee = getattr(user, "employee_get", None)
    return bool(
        employee
        and (
            meeting.employee_id.filter(pk=employee.pk).exists()
            or meeting.manager.filter(pk=employee.pk).exists()
        )
    )


def _meeting_or_403(request, room_code):
    meeting = get_object_or_404(Meetings, room_code=room_code, is_active=True)
    return meeting if _can_access(request.user, meeting) else None


def _can_control(user, meeting):
    employee = getattr(user, "employee_get", None)
    return bool(
        user.is_superuser
        or user.has_perm("pms.manage_meeting_integrations")
        or user.has_perm("pms.change_meetings")
        or (employee and meeting.manager.filter(pk=employee.pk).exists())
    )


@login_required
def meeting_room(request, room_code):
    meeting = _meeting_or_403(request, room_code)
    if not meeting:
        return HttpResponseForbidden("You are not a participant of this meeting.")
    if meeting.meeting_type == "external" and meeting.external_url:
        return redirect(meeting.external_url)
    MeetingSignal.objects.filter(
        meeting=meeting, created_at__lt=timezone.now() - timedelta(minutes=2)
    ).delete()
    participants = (meeting.manager.all() | meeting.employee_id.all()).distinct().select_related("employee_user_id")
    return render(request, "meetings/call_room.html", {"meeting": meeting, "participants": participants, "can_control": _can_control(request.user, meeting)})


@login_required
def create_meeting_shortcut(request):
    return redirect("/pms/view-meetings/?create=1")


@login_required
def meeting_reminders(request):
    now = timezone.now()
    meetings = Meetings.objects.filter(
        is_active=True,
        status__in=("scheduled", "live"),
        date__gte=now - timedelta(minutes=10),
        date__lte=now + timedelta(seconds=30),
    ).order_by("date")
    if not request.user.is_superuser and not request.user.has_perm("pms.manage_meeting_integrations"):
        employee = getattr(request.user, "employee_get", None)
        meetings = meetings.filter(employee_id=employee) | meetings.filter(manager=employee)
    return JsonResponse({"meetings": [{
        "id": item.id,
        "title": item.title,
        "start": item.date.isoformat(),
        "join_url": f"/pms/meeting-call/{item.room_code}/",
        "provider": item.get_provider_display(),
    } for item in meetings.distinct()[:5]]})


@login_required
def meeting_feed(request, room_code):
    meeting = _meeting_or_403(request, room_code)
    if not meeting:
        return JsonResponse({"detail": "Forbidden"}, status=403)
    after_message = int(request.GET.get("after_message", 0))
    after_caption = int(request.GET.get("after_caption", 0))
    after_note = int(request.GET.get("after_note", 0))
    after_recording = int(request.GET.get("after_recording", 0))
    messages = meeting.call_messages.filter(id__gt=after_message).select_related("sender")[:100]
    captions = meeting.captions.filter(id__gt=after_caption).select_related("speaker")[:100]
    notes = meeting.notes.filter(id__gt=after_note).select_related("author")[:100]
    recordings = meeting.recordings.filter(id__gt=after_recording).select_related("recorded_by")[:100]
    return JsonResponse({
        "messages": [{"id": x.id, "sender": x.sender.get_full_name() or x.sender.username, "message": x.message, "created_at": x.created_at.isoformat()} for x in messages],
        "captions": [{"id": x.id, "speaker": x.speaker.get_full_name() or x.speaker.username, "text": x.text, "language": x.language, "created_at": x.created_at.isoformat()} for x in captions],
        "notes": [{"id": x.id, "author": x.author.get_full_name() or x.author.username, "note": x.note, "created_at": x.created_at.isoformat()} for x in notes],
        "recordings": [{"id": x.id, "recorded_by": (x.recorded_by.get_full_name() or x.recorded_by.username) if x.recorded_by else "Unknown", "duration_seconds": x.duration_seconds, "created_at": x.created_at.isoformat(), "download_url": f"/pms/meeting-recording/{x.id}/download/", "delete_url": f"/pms/meeting-recording/{x.id}/delete/"} for x in recordings],
        "status": meeting.status,
    })


@login_required
@require_POST
def meeting_message(request, room_code):
    meeting = _meeting_or_403(request, room_code)
    if not meeting or not meeting.allow_chat:
        return JsonResponse({"detail": "Forbidden"}, status=403)
    message = request.POST.get("message", "").strip()
    if not message:
        return JsonResponse({"detail": "Message is required"}, status=400)
    item = MeetingMessage.objects.create(meeting=meeting, sender=request.user, message=message[:2000])
    return JsonResponse({"id": item.id}, status=201)


@login_required
@require_POST
def meeting_caption(request, room_code):
    meeting = _meeting_or_403(request, room_code)
    if not meeting or not meeting.allow_captions:
        return JsonResponse({"detail": "Forbidden"}, status=403)
    text = request.POST.get("text", "").strip()
    if not text:
        return JsonResponse({"detail": "Caption is required"}, status=400)
    item = MeetingCaption.objects.create(meeting=meeting, speaker=request.user, text=text[:4000], language=request.POST.get("language", "en-IN")[:20])
    return JsonResponse({"id": item.id}, status=201)


@login_required
@require_POST
def meeting_note(request, room_code):
    meeting = _meeting_or_403(request, room_code)
    if not meeting:
        return JsonResponse({"detail": "Forbidden"}, status=403)
    note = request.POST.get("note", "").strip()
    if not note:
        return JsonResponse({"detail": "Note is required"}, status=400)
    item = MeetingNote.objects.create(meeting=meeting, author=request.user, note=note[:5000])
    return JsonResponse({"id": item.id}, status=201)


@login_required
@require_http_methods(["GET", "POST"])
def meeting_signal(request, room_code):
    meeting = _meeting_or_403(request, room_code)
    if not meeting:
        return JsonResponse({"detail": "Forbidden"}, status=403)
    if request.method == "POST":
        data = json.loads(request.body or "{}")
        recipient_id = data.get("recipient_id")
        signal_type = data.get("type", "candidate")[:20]
        if signal_type == "control":
            if not _can_control(request.user, meeting):
                return JsonResponse({"detail": "Host control permission required"}, status=403)
            allowed_users = set(meeting.manager.values_list("employee_user_id_id", flat=True)) | set(meeting.employee_id.values_list("employee_user_id_id", flat=True))
            if not recipient_id or int(recipient_id) not in allowed_users:
                return JsonResponse({"detail": "Recipient is not a meeting participant"}, status=400)
        signal = MeetingSignal.objects.create(meeting=meeting, sender=request.user, recipient_id=recipient_id or None, signal_type=data.get("type", "candidate")[:20], payload=data.get("payload", {}))
        return JsonResponse({"id": signal.id}, status=201)
    after = int(request.GET.get("after", 0))
    signals = MeetingSignal.objects.filter(meeting=meeting, id__gt=after).exclude(sender=request.user).filter(recipient__isnull=True) | MeetingSignal.objects.filter(meeting=meeting, id__gt=after, recipient=request.user).exclude(sender=request.user)
    signals = signals.select_related("sender").order_by("id")[:100]
    return JsonResponse({"signals": [{"id": x.id, "sender_id": x.sender_id, "sender": x.sender.username, "type": x.signal_type, "payload": x.payload} for x in signals]})


@login_required
@permission_required("pms.record_meeting_call", raise_exception=True)
@require_POST
def meeting_recording(request, room_code):
    meeting = _meeting_or_403(request, room_code)
    if not meeting or not meeting.allow_recording:
        return JsonResponse({"detail": "Forbidden"}, status=403)
    upload = request.FILES.get("recording")
    if not upload:
        return JsonResponse({"detail": "Recording file is required"}, status=400)
    item = MeetingRecording.objects.create(meeting=meeting, recorded_by=request.user, file=upload, duration_seconds=int(request.POST.get("duration_seconds", 0)))
    return JsonResponse({"id": item.id, "url": item.file.url}, status=201)


@login_required
def recording_download(request, recording_id):
    item = get_object_or_404(MeetingRecording.objects.select_related("meeting"), pk=recording_id)
    if not _can_access(request.user, item.meeting):
        return HttpResponseForbidden("Forbidden")
    return FileResponse(item.file.open("rb"), as_attachment=True, filename=item.file.name.rsplit("/", 1)[-1])


@login_required
@permission_required("pms.delete_meetingrecording", raise_exception=True)
@require_POST
def recording_delete(request, recording_id):
    item = get_object_or_404(MeetingRecording.objects.select_related("meeting"), pk=recording_id)
    if not _can_access(request.user, item.meeting):
        return JsonResponse({"detail": "Forbidden"}, status=403)
    try:
        item.file.delete(save=False)
    except PermissionError:
        return JsonResponse({"detail": "Recording is currently being downloaded. Close the download and retry."}, status=409)
    item.delete()
    return JsonResponse({"deleted": True})


@login_required
@permission_required("pms.manage_meeting_integrations", raise_exception=True)
@require_http_methods(["GET", "POST"])
def provider_settings(request):
    employee = getattr(request.user, "employee_get", None)
    company = getattr(getattr(employee, "employee_work_info", None), "company_id", None)
    if request.method == "POST" and company:
        provider = request.POST.get("provider")
        item, _ = MeetingProviderConfig.objects.get_or_create(company_id=company, provider=provider)
        for field in ("client_id", "client_secret", "access_token", "account_id", "tenant_id", "api_base_url"):
            value = request.POST.get(field)
            if value:
                setattr(item, field, value)
        item.is_active = request.POST.get("is_active") == "on"
        item.save()
        return redirect("meeting-provider-settings")
    configs = MeetingProviderConfig.objects.filter(company_id=company) if company else MeetingProviderConfig.objects.none()
    return render(request, "meetings/provider_settings.html", {"configs": configs})


@login_required
@permission_required("pms.manage_meeting_integrations", raise_exception=True)
@require_POST
def provision_provider_meeting(request, meeting_id):
    meeting = get_object_or_404(Meetings, pk=meeting_id)
    try:
        meeting.external_url = provision_external_meeting(meeting, request.POST.get("provider"))
        meeting.provider = request.POST.get("provider")
        meeting.meeting_type = "external"
        meeting.save()
        messages.success(request, f"{meeting.get_provider_display()} meeting created successfully.")
        return redirect("view-meetings")
    except Exception as exc:
        messages.error(request, str(exc))
        return redirect("view-meetings")
