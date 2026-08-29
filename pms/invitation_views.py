import json
from datetime import timedelta

from django.contrib import messages
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.utils.translation import gettext as _

from .models import MeetingInvitation, Meetings
from .serializers import MeetingInvitationSerializer
from chhabi.decorators import permission_required

# Default expiry hours (can be adjusted via settings)
MEETING_INVITATION_DEFAULT_EXPIRY_HOURS = getattr(
    __import__("django.conf").conf.settings, "MEETING_INVITATION_DEFAULT_EXPIRY_HOURS", 24
)

@login_required
@permission_required(perm="pms.manage_meeting_integrations")
@require_http_methods(["POST"])
def create_meeting_invitation(request, meeting_id):
    """Create a secure invitation for a meeting.

    Expected JSON payload:
        {
            "expires_at": "2024-12-31T23:59:00Z",   # optional
            "password": "secret",                  # optional
            "waiting_room": true                    # optional
        }
    """
    meeting = get_object_or_404(Meetings, id=meeting_id)
    try:
        data = json.loads(request.body)
    except Exception:
        return HttpResponseBadRequest("Invalid JSON payload")

    serializer = MeetingInvitationSerializer(data=data)
    if not serializer.is_valid():
        return JsonResponse(serializer.errors, status=400)

    invitation = serializer.save(meeting=meeting, created_by=request.user)
    # Ensure expiry if not provided
    if not invitation.expires_at:
        invitation.expires_at = timezone.now() + timedelta(hours=MEETING_INVITATION_DEFAULT_EXPIRY_HOURS)
        invitation.save()

    response_data = {
        "id": invitation.id,
        "join_url": invitation.join_url,
        "expires_at": invitation.expires_at,
        "revoked": invitation.revoked,
    }
    return JsonResponse(response_data, status=201)

@login_required
@permission_required(perm="pms.manage_meeting_integrations")
@require_http_methods(["POST"])
def revoke_meeting_invitation(request, meeting_id, token):
    """Revoke an existing invitation (soft‑delete)."""
    invitation = get_object_or_404(MeetingInvitation, meeting_id=meeting_id, token=token)
    invitation.revoked = True
    invitation.save()
    messages.success(request, _("Invitation revoked successfully"))
    return HttpResponse(status=204)

@login_required
@require_http_methods(["GET"])
def join_meeting_invitation(request, meeting_id, token):
    """Validate an invitation token and return meeting details.
    If a password is set on the invitation, it must be supplied via the
    ``password`` query parameter.
    """
    invitation = get_object_or_404(MeetingInvitation, meeting_id=meeting_id, token=token)
    if invitation.revoked:
        return HttpResponseBadRequest("Invitation has been revoked")
    if invitation.expires_at and timezone.now() > invitation.expires_at:
        return HttpResponseBadRequest("Invitation has expired")
    password = request.GET.get("password")
    if invitation.password and invitation.password != password:
        return HttpResponseBadRequest("Invalid password")

    # At this point the token is valid – return minimal meeting info.
    meeting = invitation.meeting
    data = {
        "meeting_id": meeting.id,
        "title": meeting.title,
        "start_time": meeting.start_time,
        "join_url": reverse("pms:meeting-invitation-join", kwargs={"meeting_id": meeting.id, "token": invitation.token}),
    }
    return JsonResponse(data)
