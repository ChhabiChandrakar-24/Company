"""External meeting provider adapters."""

from requests import post
import uuid

from .models import MeetingProviderConfig


def provision_external_meeting(meeting, provider):
    config = MeetingProviderConfig.objects.get(
        company_id=meeting.company_id, provider=provider, is_active=True
    )
    if provider == "zoom":
        token_response = post(
            "https://zoom.us/oauth/token",
            params={"grant_type": "account_credentials", "account_id": config.account_id},
            auth=(config.client_id, config.client_secret),
            timeout=20,
        )
        token_response.raise_for_status()
        token = token_response.json()["access_token"]
        response = post(
            "https://api.zoom.us/v2/users/me/meetings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "topic": meeting.title,
                "type": 2,
                "start_time": meeting.date.isoformat() if meeting.date else None,
                "duration": max(1, int(((meeting.end_date - meeting.date).total_seconds() / 60))) if meeting.date and meeting.end_date else 30,
                "agenda": meeting.description,
                "settings": {"auto_recording": "cloud" if meeting.allow_recording else "none", "waiting_room": True},
            },
            timeout=20,
        )
        response.raise_for_status()
        return response.json()["join_url"]
    if provider == "custom":
        response = post(
            config.api_base_url,
            json={"title": meeting.title, "start": meeting.date.isoformat() if meeting.date else None, "end": meeting.end_date.isoformat() if meeting.end_date else None, "room_code": str(meeting.room_code)},
            headers={"X-Client-Id": config.client_id, "X-Client-Secret": config.client_secret},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("join_url") or data.get("url")
    if provider == "google_meet":
        if not config.access_token:
            raise ValueError("Google OAuth access token is required")
        response = post(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events?conferenceDataVersion=1",
            headers={"Authorization": f"Bearer {config.access_token}"},
            json={
                "summary": meeting.title,
                "description": meeting.description,
                "start": {"dateTime": meeting.date.isoformat()},
                "end": {"dateTime": meeting.end_date.isoformat()},
                "conferenceData": {"createRequest": {"requestId": str(uuid.uuid4()), "conferenceSolutionKey": {"type": "hangoutsMeet"}}},
            }, timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("hangoutLink") or data["conferenceData"]["entryPoints"][0]["uri"]
    if provider == "teams":
        if not config.access_token:
            raise ValueError("Microsoft Graph OAuth access token is required")
        response = post(
            "https://graph.microsoft.com/v1.0/me/onlineMeetings",
            headers={"Authorization": f"Bearer {config.access_token}"},
            json={"subject": meeting.title, "startDateTime": meeting.date.isoformat(), "endDateTime": meeting.end_date.isoformat()},
            timeout=20,
        )
        response.raise_for_status()
        return response.json()["joinWebUrl"]
    raise ValueError("Unsupported meeting provider")
