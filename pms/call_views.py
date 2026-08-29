import json
from datetime import timedelta

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import FileResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt

from .models import (
    MeetingCaption,
    MeetingGuestToken,
    MeetingMessage,
    MeetingNote,
    MeetingProviderConfig,
    MeetingRecording,
    MeetingSignal,
    Meetings,
)
from .meeting_providers import provision_external_meeting


def _display_name(user):
    """Return clean human-readable name, avoiding raw email IDs."""
    if not user:
        return "Participant"
    employee = getattr(user, "employee_get", None)
    if employee:
        emp_name = employee.get_full_name()
        if emp_name and emp_name.strip():
            return emp_name.strip()
    full_name = user.get_full_name()
    if full_name and full_name.strip():
        return full_name.strip()
    raw = user.username or ""
    if "@" in raw:
        raw = raw.split("@")[0]
    clean = raw.replace(".", " ").replace("_", " ").strip().title()
    return clean or "Participant"


def _get_guest_token(request, meeting):
    """Check if request has a valid external guest token."""
    token_str = (
        request.GET.get("token")
        or request.POST.get("token")
        or request.headers.get("X-Guest-Token")
        or request.session.get(f"guest_token_{meeting.id}")
    )
    if not token_str:
        return None

    guest_token = (
        MeetingGuestToken.objects.filter(meeting=meeting, token=token_str, is_revoked=False)
        .filter(expires_at__gte=timezone.now())
        .first()
    )
    if guest_token:
        request.session[f"guest_token_{meeting.id}"] = token_str
    return guest_token


def _can_access(user, meeting, request=None):
    """Check or grant access for direct link joiners or guest tokens."""
    if request:
        guest_token = _get_guest_token(request, meeting)
        if guest_token:
            return True

    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff or user.has_perm("pms.manage_meeting_integrations") or user.has_perm("pms.join_meeting_call"):
        return True
    employee = getattr(user, "employee_get", None)
    if employee:
        if meeting.employee_id.filter(pk=employee.pk).exists() or meeting.manager.filter(pk=employee.pk).exists():
            return True
        # Auto-enroll employee visiting valid room link
        meeting.employee_id.add(employee)
        return True
    return True


def _meeting_or_403(request, room_code):
    meeting = get_object_or_404(Meetings, room_code=room_code, is_active=True)
    return meeting if _can_access(request.user, meeting, request) else None


def _can_control(user, meeting, request=None):
    if request:
        guest_token = _get_guest_token(request, meeting)
        if guest_token and guest_token.guest_role == "host":
            return True

    if not user or not user.is_authenticated:
        return False
    employee = getattr(user, "employee_get", None)
    return bool(
        user.is_superuser
        or user.is_staff
        or user.has_perm("pms.manage_meeting_integrations")
        or user.has_perm("pms.change_meetings")
        or (employee and meeting.manager.filter(pk=employee.pk).exists())
    )


def meeting_room(request, room_code):
    """
    Renders video call room for internal logged-in users OR external guests with valid signed tokens.
    """
    meeting = get_object_or_404(Meetings, room_code=room_code, is_active=True)

    guest_token = _get_guest_token(request, meeting)
    if not guest_token and not request.user.is_authenticated:
        return redirect(f"/accounts/login/?next={request.path}")

    if not _can_access(request.user, meeting, request):
        return HttpResponseForbidden("You do not have access to this meeting room.")

    if meeting.meeting_type == "external" and meeting.external_url:
        return redirect(meeting.external_url)

    # Clean old signals
    MeetingSignal.objects.filter(
        meeting=meeting, created_at__lt=timezone.now() - timedelta(minutes=5)
    ).delete()

    if request.user.is_authenticated:
        employee = getattr(request.user, "employee_get", None)
        if employee and not meeting.employee_id.filter(pk=employee.pk).exists() and not meeting.manager.filter(pk=employee.pk).exists():
            meeting.employee_id.add(employee)
        current_user_name = _display_name(request.user)
        current_user_id = request.user.id
        can_control = _can_control(request.user, meeting, request)
    else:
        current_user_name = guest_token.guest_name
        current_user_id = 900000 + guest_token.id
        can_control = (guest_token.guest_role == "host")

    participants = (meeting.manager.all() | meeting.employee_id.all()).distinct().select_related("employee_user_id")
    participants_data = []
    for p in participants:
        u = getattr(p, "employee_user_id", None)
        participants_data.append({
            "id": p.id,
            "user_id": u.id if u else None,
            "name": p.get_full_name(),
            "is_manager": meeting.manager.filter(pk=p.pk).exists(),
        })

    join_url = request.build_absolute_uri(f"/pms/meeting-call/{meeting.room_code}/")
    if guest_token:
        join_url += f"?token={guest_token.token}"

    return render(
        request,
        "meetings/call_room.html",
        {
            "meeting": meeting,
            "participants": participants,
            "participants_data": participants_data,
            "can_control": can_control,
            "current_user_name": current_user_name,
            "current_user_id": current_user_id,
            "join_url": join_url,
            "is_guest": bool(guest_token),
        },
    )


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
    return JsonResponse({
        "meetings": [
            {
                "id": item.id,
                "title": item.title,
                "start": item.date.isoformat() if item.date else None,
                "join_url": f"/pms/meeting-call/{item.room_code}/",
                "provider": item.get_provider_display(),
            }
            for item in meetings.distinct()[:5]
        ]
    })


def meeting_feed(request, room_code):
    meeting = _meeting_or_403(request, room_code)
    if not meeting:
        return JsonResponse({"detail": "Forbidden"}, status=403)
    after_message = int(request.GET.get("after_message", 0))
    after_caption = int(request.GET.get("after_caption", 0))
    after_note = int(request.GET.get("after_note", 0))
    after_recording = int(request.GET.get("after_recording", 0))

    messages_qs = meeting.call_messages.filter(id__gt=after_message).select_related("sender")[:100]
    captions_qs = meeting.captions.filter(id__gt=after_caption).select_related("speaker")[:100]
    notes_qs = meeting.notes.filter(id__gt=after_note).select_related("author")[:100]
    recordings_qs = meeting.recordings.filter(id__gt=after_recording).select_related("recorded_by")[:100]

    return JsonResponse({
        "messages": [
            {
                "id": x.id,
                "sender_id": x.sender_id,
                "sender": _display_name(x.sender),
                "message": x.message,
                "created_at": x.created_at.strftime("%I:%M %p"),
                "iso_time": x.created_at.isoformat(),
            }
            for x in messages_qs
        ],
        "captions": [
            {
                "id": x.id,
                "speaker_id": x.speaker_id,
                "speaker": _display_name(x.speaker),
                "text": x.text,
                "language": x.language,
                "created_at": x.created_at.isoformat(),
            }
            for x in captions_qs
        ],
        "notes": [
            {
                "id": x.id,
                "author_id": x.author_id,
                "author": _display_name(x.author),
                "note": x.note,
                "created_at": x.created_at.strftime("%I:%M %p"),
                "iso_time": x.created_at.isoformat(),
            }
            for x in notes_qs
        ],
        "recordings": [
            {
                "id": x.id,
                "recorded_by": _display_name(x.recorded_by) if x.recorded_by else "Host",
                "duration_seconds": x.duration_seconds,
                "created_at": x.created_at.strftime("%d %b %Y, %I:%M %p"),
                "download_url": f"/pms/meeting-recording/{x.id}/download/",
                "delete_url": f"/pms/meeting-recording/{x.id}/delete/",
            }
            for x in recordings_qs
        ],
        "status": meeting.status,
    })


@require_POST
def meeting_message(request, room_code):
    meeting = _meeting_or_403(request, room_code)
    if not meeting or not meeting.allow_chat:
        return JsonResponse({"detail": "Forbidden"}, status=403)
    message = request.POST.get("message", "").strip()
    if not message:
        return JsonResponse({"detail": "Message is required"}, status=400)

    user = request.user if request.user.is_authenticated else (User.objects.filter(is_superuser=True).first() or User.objects.first())
    guest_token = _get_guest_token(request, meeting)
    display_sender = guest_token.guest_name if guest_token else _display_name(user)
    sender_id = (900000 + guest_token.id) if guest_token else (user.id if user else 1)

    item = MeetingMessage.objects.create(meeting=meeting, sender=user, message=message[:2000])
    return JsonResponse({
        "id": item.id,
        "sender": display_sender,
        "sender_id": sender_id,
        "message": item.message,
        "created_at": item.created_at.strftime("%I:%M %p"),
    }, status=201)


@require_POST
def meeting_caption(request, room_code):
    meeting = _meeting_or_403(request, room_code)
    if not meeting or not meeting.allow_captions:
        return JsonResponse({"detail": "Forbidden"}, status=403)
    text = request.POST.get("text", "").strip()
    if not text:
        return JsonResponse({"detail": "Caption is required"}, status=400)

    user = request.user if request.user.is_authenticated else User.objects.filter(is_superuser=True).first()
    guest_token = _get_guest_token(request, meeting)
    speaker_name = guest_token.guest_name if guest_token else _display_name(user)

    item = MeetingCaption.objects.create(
        meeting=meeting,
        speaker=user,
        text=text[:4000],
        language=request.POST.get("language", "en-IN")[:20],
    )
    return JsonResponse({
        "id": item.id,
        "speaker": speaker_name,
        "text": item.text,
        "language": item.language,
    }, status=201)


@require_POST
def meeting_note(request, room_code):
    meeting = _meeting_or_403(request, room_code)
    if not meeting:
        return JsonResponse({"detail": "Forbidden"}, status=403)
    note = request.POST.get("note", "").strip()
    if not note:
        return JsonResponse({"detail": "Note is required"}, status=400)

    user = request.user if request.user.is_authenticated else User.objects.filter(is_superuser=True).first()
    guest_token = _get_guest_token(request, meeting)
    author_name = guest_token.guest_name if guest_token else _display_name(user)

    item = MeetingNote.objects.create(meeting=meeting, author=user, note=note[:5000])
    return JsonResponse({
        "id": item.id,
        "author": author_name,
        "note": item.note,
        "created_at": item.created_at.strftime("%I:%M %p"),
    }, status=201)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def meeting_signal(request, room_code):
    meeting = _meeting_or_403(request, room_code)
    if not meeting:
        return JsonResponse({"detail": "Forbidden"}, status=403)

    user = request.user if request.user.is_authenticated else User.objects.filter(is_superuser=True).first()
    guest_token = _get_guest_token(request, meeting)
    my_id = (900000 + guest_token.id) if guest_token else (user.id if user else 1)
    my_name = guest_token.guest_name if guest_token else _display_name(user)

    if request.method == "POST":
        data = json.loads(request.body or "{}")
        recipient_id = data.get("recipient_id")
        signal_type = data.get("type", "candidate")[:30]

        if signal_type == "control":
            if not _can_control(request.user, meeting, request):
                return JsonResponse({"detail": "Host control permission required"}, status=403)

        signal_payload = data.get("payload", {})
        if not signal_payload.get("sender_id"):
            signal_payload["sender_id"] = my_id
        if not signal_payload.get("sender_name"):
            signal_payload["sender_name"] = my_name

        signal = MeetingSignal.objects.create(
            meeting=meeting,
            sender=user,
            recipient_id=recipient_id if (recipient_id and recipient_id < 900000) else None,
            signal_type=signal_type,
            payload=signal_payload,
        )
        return JsonResponse({"id": signal.id}, status=201)

    after = int(request.GET.get("after", 0))
    signals = (
        MeetingSignal.objects.filter(meeting=meeting, id__gt=after)
        .exclude(sender=user)
        .filter(recipient__isnull=True)
        | MeetingSignal.objects.filter(meeting=meeting, id__gt=after, recipient=user).exclude(
            sender=user
        )
    )
    signals = signals.select_related("sender").order_by("id")[:150]
    return JsonResponse({
        "signals": [
            {
                "id": x.id,
                "sender_id": x.payload.get("sender_id", x.sender_id),
                "sender": x.payload.get("sender_name", _display_name(x.sender)),
                "type": x.signal_type,
                "payload": x.payload,
                "recipient_id": x.recipient_id,
            }
            for x in signals
        ]
    })


@require_POST
def meeting_recording(request, room_code):
    meeting = _meeting_or_403(request, room_code)
    if not meeting or not meeting.allow_recording:
        return JsonResponse({"detail": "Forbidden"}, status=403)
    upload = request.FILES.get("recording")
    if not upload:
        return JsonResponse({"detail": "Recording file is required"}, status=400)

    user = request.user if request.user.is_authenticated else None
    item = MeetingRecording.objects.create(
        meeting=meeting,
        recorded_by=user,
        file=upload,
        duration_seconds=int(request.POST.get("duration_seconds", 0)),
    )
    return JsonResponse({"id": item.id, "url": item.file.url}, status=201)


def recording_download(request, recording_id):
    item = get_object_or_404(MeetingRecording.objects.select_related("meeting"), pk=recording_id)
    if not _can_access(request.user, item.meeting, request):
        return HttpResponseForbidden("Forbidden")
    return FileResponse(item.file.open("rb"), as_attachment=True, filename=item.file.name.rsplit("/", 1)[-1])


@login_required
@permission_required("pms.delete_meetingrecording", raise_exception=True)
@require_POST
def recording_delete(request, recording_id):
    item = get_object_or_404(MeetingRecording.objects.select_related("meeting"), pk=recording_id)
    if not _can_access(request.user, item.meeting, request):
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
