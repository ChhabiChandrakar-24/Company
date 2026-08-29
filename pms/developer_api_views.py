import json
import secrets
import uuid
from datetime import timedelta
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .entitlement import EntitlementError
from pms.models import (
    Meetings,
    MeetingGuestToken,
    DeveloperApiKey,
    UserSubscription,
    MeetingPlan,
    MeetingRecording,
)


def require_developer_api_key(view_func):
    """
    Decorator for public Developer REST API endpoints.
    Authenticates via headers:
      - X-API-Key: <key>
      - X-API-Secret: <secret>
    or Authorization: Bearer <key>
    """
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        api_key_str = (
            request.headers.get("X-API-Key")
            or request.headers.get("x-api-key")
            or request.META.get("HTTP_X_API_KEY")
            or request.GET.get("api_key")
        )
        api_secret_str = (
            request.headers.get("X-API-Secret")
            or request.headers.get("x-api-secret")
            or request.META.get("HTTP_X_API_SECRET")
            or request.GET.get("api_secret")
        )

        auth_header = request.headers.get("Authorization", "") or request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Bearer "):
            bearer_token = auth_header[7:].strip()
            if not api_key_str:
                api_key_str = bearer_token

        if not api_key_str:
            return JsonResponse(
                {
                    "error": "Authentication failed",
                    "code": "MISSING_API_KEY",
                    "message": "Please provide your API Key via 'X-API-Key' header or 'Authorization: Bearer <key>'.",
                },
                status=401,
            )

        api_key_obj = (
            DeveloperApiKey.objects.filter(api_key=api_key_str, is_active=True)
            .select_related("user", "subscription", "subscription__plan")
            .first()
        )

        if not api_key_obj:
            return JsonResponse(
                {
                    "error": "Invalid API Key",
                    "code": "INVALID_API_KEY",
                    "message": "The provided API key does not exist or has been revoked.",
                },
                status=401,
            )

        if api_secret_str and api_key_obj.api_secret != api_secret_str:
            return JsonResponse(
                {
                    "error": "Invalid API Secret",
                    "code": "INVALID_API_SECRET",
                    "message": "The provided API secret is incorrect.",
                },
                status=401,
            )

        # Check Subscription Plan Entitlement
        sub = api_key_obj.subscription
        if not sub or not sub.is_currently_active:
            # Fallback check if user has another active subscription
            sub = (
                UserSubscription.objects.filter(user=api_key_obj.user, status="active")
                .select_related("plan")
                .first()
            )

        request.developer_app = api_key_obj
        request.developer_user = api_key_obj.user
        request.developer_subscription = sub
        request.organization = sub.organization if sub else None

        # Re-instantiate entitlement service now that developer variables and organization are attached
        from pms.entitlement import EntitlementService
        request.entitlement = EntitlementService(request)

        # Verify developer API feature entitlement
        try:
            request.entitlement.check_feature('developer_api')
        except EntitlementError as e:
            return e.get_response()

        # Update metrics
        api_key_obj.total_requests += 1
        api_key_obj.last_used_at = timezone.now()
        api_key_obj.save(update_fields=["total_requests", "last_used_at"])

        return view_func(request, *args, **kwargs)

    return wrapped_view


def _create_guest_token(meeting, app, guest_name, guest_role="participant", guest_email="", expiry_hours=24):
    """Helper to generate a signed guest token for third-party participants."""
    token_str = f"gt_{secrets.token_urlsafe(32)}"
    expires_at = timezone.now() + timedelta(hours=expiry_hours)

    token_obj = MeetingGuestToken.objects.create(
        meeting=meeting,
        api_key=app,
        token=token_str,
        guest_name=guest_name or "Guest Attendee",
        guest_email=guest_email,
        guest_role=guest_role,
        expires_at=expires_at,
    )
    return token_obj


# ============================================================================
# PUBLIC DEVELOPER REST API (Zoom-Like Endpoints)
# ============================================================================

@csrf_exempt
@require_developer_api_key
def api_create_meeting(request):
    """
    POST /pms/api/v1/meetings/create/
    Zoom equivalent: POST /v1/users/me/meetings

    Payload (JSON):
    {
      "title": "Client Onboarding Video Call",
      "start_date": "2026-08-27T10:00:00",
      "end_date": "2026-08-27T11:00:00",
      "host_name": "Dr. Sarah (Host)",
      "guest_name": "John Doe (Patient)",
      "allow_recording": true,
      "allow_chat": true,
      "allow_captions": true,
      "max_participants": 10
    }
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed. Use POST."}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        data = request.POST

    title = data.get("title", "").strip() or f"Video Call ({timezone.now().strftime('%d %b %H:%M')})"
    start_date_str = data.get("start_date")
    end_date_str = data.get("end_date")

    now = timezone.now()
    start_date = timezone.datetime.fromisoformat(start_date_str) if start_date_str else now
    end_date = timezone.datetime.fromisoformat(end_date_str) if end_date_str else (start_date + timedelta(hours=1))

    if timezone.is_naive(start_date):
        start_date = timezone.make_aware(start_date)
    if timezone.is_naive(end_date):
        end_date = timezone.make_aware(end_date)

    allow_recording = bool(data.get("allow_recording", True))
    allow_chat = bool(data.get("allow_chat", True))
    allow_captions = bool(data.get("allow_captions", True))

    try:
        # Consume a room creation quota for this meeting before writing it to DB
        request.entitlement.consume_quota('rooms_created_today')
    except EntitlementError as e:
        return e.get_response()

    meeting = Meetings.objects.create(
        title=title,
        date=start_date,
        end_date=end_date,
        allow_recording=allow_recording,
        allow_chat=allow_chat,
        allow_captions=allow_captions,
        meeting_type="internal",
        provider="internal",
        organization=request.organization,
    )

    # Generate Host and Participant guest tokens
    host_name = data.get("host_name") or f"{request.developer_user.get_full_name() or request.developer_user.username} (Host)"
    participant_name = data.get("guest_name") or "Guest Participant"

    host_token_obj = _create_guest_token(meeting, request.developer_app, guest_name=host_name, guest_role="host")
    part_token_obj = _create_guest_token(meeting, request.developer_app, guest_name=participant_name, guest_role="participant")

    base_room_url = request.build_absolute_uri(f"/pms/meeting-call/{meeting.room_code}/")
    host_join_url = f"{base_room_url}?token={host_token_obj.token}"
    part_join_url = f"{base_room_url}?token={part_token_obj.token}"

    return JsonResponse(
        {
            "status": "success",
            "meeting_id": meeting.id,
            "room_code": str(meeting.room_code),
            "title": meeting.title,
            "start_time": meeting.date.isoformat() if meeting.date else now.isoformat(),
            "end_time": meeting.end_date.isoformat() if meeting.end_date else (now + timedelta(hours=1)).isoformat(),
            "join_url_host": host_join_url,
            "join_url_participant": part_join_url,
            "host_token": host_token_obj.token,
            "participant_token": part_token_obj.token,
            "allow_recording": meeting.allow_recording,
            "allow_chat": meeting.allow_chat,
            "allow_captions": meeting.allow_captions,
            "created_at": meeting.created_at.isoformat() if hasattr(meeting, "created_at") and meeting.created_at else now.isoformat(),
        },
        status=201,
    )


@csrf_exempt
@require_developer_api_key
def api_get_meeting(request, meeting_id):
    """
    GET /pms/api/v1/meetings/<id>/
    Returns meeting details, status, and active recordings count.
    """
    meeting = get_object_or_404(Meetings, id=meeting_id)

    recordings_count = meeting.recordings.count()
    guest_tokens_count = meeting.guest_tokens.count()

    base_room_url = request.build_absolute_uri(f"/pms/meeting-call/{meeting.room_code}/")

    return JsonResponse({
        "id": meeting.id,
        "room_code": str(meeting.room_code),
        "title": meeting.title,
        "start_time": meeting.date.isoformat() if meeting.date else None,
        "end_time": meeting.end_date.isoformat() if meeting.end_date else None,
        "room_url": base_room_url,
        "allow_recording": meeting.allow_recording,
        "allow_chat": meeting.allow_chat,
        "allow_captions": meeting.allow_captions,
        "recordings_count": recordings_count,
        "issued_tokens_count": guest_tokens_count,
    })


@csrf_exempt
@require_developer_api_key
def api_generate_join_token(request, meeting_id):
    """
    POST /pms/api/v1/meetings/<id>/join-token/
    Generates a new signed join token for a specific attendee.

    Payload:
    {
      "guest_name": "Rohan Sharma",
      "guest_email": "rohan@example.com",
      "guest_role": "participant",  // or "host"
      "expiry_hours": 48
    }
    """
    meeting = get_object_or_404(Meetings, id=meeting_id)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        data = request.POST

    guest_name = data.get("guest_name", "").strip() or "Guest Attendee"
    guest_email = data.get("guest_email", "").strip()
    guest_role = data.get("guest_role", "participant").lower()
    if guest_role not in ["host", "participant"]:
        guest_role = "participant"

    expiry_hours = int(data.get("expiry_hours", 24))

    token_obj = _create_guest_token(
        meeting,
        request.developer_app,
        guest_name=guest_name,
        guest_role=guest_role,
        guest_email=guest_email,
        expiry_hours=expiry_hours,
    )

    base_room_url = request.build_absolute_uri(f"/pms/meeting-call/{meeting.room_code}/")
    join_url = f"{base_room_url}?token={token_obj.token}"

    return JsonResponse({
        "status": "success",
        "meeting_id": meeting.id,
        "guest_name": token_obj.guest_name,
        "guest_role": token_obj.guest_role,
        "join_url": join_url,
        "token": token_obj.token,
        "expires_at": token_obj.expires_at.isoformat(),
    })


@csrf_exempt
@require_developer_api_key
def api_list_recordings(request, meeting_id):
    """
    GET /pms/api/v1/meetings/<id>/recordings/
    Lists all saved recordings for the meeting with direct download URLs.
    """
    meeting = get_object_or_404(Meetings, id=meeting_id)
    recs = meeting.recordings.all().order_by("-created_at")

    recordings_list = []
    for r in recs:
        recordings_list.append({
            "id": r.id,
            "duration_seconds": r.duration_seconds,
            "download_url": request.build_absolute_uri(r.file.url) if r.file else None,
            "created_at": r.created_at.isoformat(),
        })

    return JsonResponse({
        "meeting_id": meeting.id,
        "title": meeting.title,
        "recordings_count": len(recordings_list),
        "recordings": recordings_list,
    })


@csrf_exempt
@require_developer_api_key
def api_developer_usage(request):
    """
    GET /pms/api/v1/developer/usage/
    Returns current developer app statistics, subscription limits, and usage quota.
    """
    app = request.developer_app
    sub = request.developer_subscription
    plan = sub.plan if sub else None

    return JsonResponse({
        "app_name": app.app_name,
        "api_key": app.api_key,
        "total_requests": app.total_requests,
        "rate_limit_per_minute": app.rate_limit_per_minute,
        "last_used_at": app.last_used_at.isoformat() if app.last_used_at else None,
        "plan": {
            "name": plan.name if plan else "None",
            "code": plan.code if plan else "none",
            "max_participants_per_room": plan.max_participants if plan else 2,
            "max_duration_minutes": plan.max_duration_minutes if plan else 40,
            "allow_cloud_recording": plan.allow_cloud_recording if plan else False,
            "max_api_calls_per_day": plan.max_api_calls_per_day if plan else 100,
        } if plan else None,
    })


# ============================================================================
# DEVELOPER PORTAL UI (API Keys Management & Documentation)
# ============================================================================

@login_required
def developer_portal_view(request):
    """
    Developer Portal dashboard to manage API keys, view interactive docs, and code samples.
    """
    api_keys = DeveloperApiKey.objects.filter(user=request.user)
    active_sub = (
        UserSubscription.objects.filter(user=request.user, status="active")
        .select_related("plan")
        .first()
    )

    base_url = request.build_absolute_uri("/pms/api/v1/")

    return render(
        request,
        "developer/developer_portal.html",
        {
            "api_keys": api_keys,
            "active_sub": active_sub,
            "base_api_url": base_url,
        },
    )


@login_required
def generate_api_key_view(request):
    """
    POST: Generates a new API Key & Secret pair.
    """
    if request.method != "POST":
        return redirect("developer-portal")

    app_name = request.POST.get("app_name", "").strip() or f"App #{uuid.uuid4().hex[:6]}"
    webhook_url = request.POST.get("webhook_url", "").strip()

    active_sub = (
        UserSubscription.objects.filter(user=request.user, status="active").first()
    )

    new_key = f"hrz_live_{secrets.token_hex(16)}"
    new_secret = f"sec_{secrets.token_urlsafe(32)}"

    key_obj = DeveloperApiKey.objects.create(
        user=request.user,
        subscription=active_sub,
        app_name=app_name,
        api_key=new_key,
        api_secret=new_secret,
        webhook_url=webhook_url,
    )

    return redirect("developer-portal")


@login_required
def revoke_api_key_view(request, key_id):
    """
    Revokes / deletes an API Key.
    """
    key_obj = get_object_or_404(DeveloperApiKey, id=key_id, user=request.user)
    key_obj.delete()
    return redirect("developer-portal")
