# Meeting Enhancements Implementation Plan

## Goal Description
Add two major enhancements to the existing meeting module:
1. **Professional participant management** – real‑time participant list, status indicators, host badge, role‑based permissions, and host controls (admit/remove, lock, mute, video permissions, end meeting).
2. **Recording support** – enable authorized users to start/stop a genuine client‑side recording of the meeting, display a recording banner with a live timer, synchronize recording state across participants, and store recording metadata linked to the meeting.

Both features must integrate with the current long‑polling signaling (`/meeting-call/<room_code>/signal/`) and WebRTC mesh architecture without introducing external real‑time services.

---
## User Review Required
[!IMPORTANT] Please confirm the following design decisions before any code changes are made:
- **Participant Management**: Use a new `MeetingParticipant` model (or extend the existing many‑to‑many) to track join/leave time, audio/video flags, and role. Add boolean fields `is_locked`, `allow_participant_video`, `allow_participant_audio` to `Meetings`.
- **Recording Storage**: Recordings will be captured client‑side using the browser `MediaRecorder` API and uploaded to the server as a file (e.g., to `media/recordings/`). The `Meeting` model will gain a `recording_file` `FileField` and fields `recording_started_at`, `recording_ended_at`, `recording_duration`.
- **Permissions**: Define Django groups/permissions (`SuperAdmin`, `PlatformAdmin`, `OrgOwner`, `MeetingHost`, `MeetingParticipant`). Confirm whether these groups already exist or need to be created.
- **Lock Behaviour**: Should a locked meeting prevent *any* new joins (including token guests) until unlocked?
- **Retention**: Any retention policy for stored recordings (e.g., 30 days)?

---
## Open Questions
- Should the participant list be paginated for very large meetings?
- Do you want the host to be able to request a participant to start video/audio, or only to mute/disable?
- Will recordings be stored permanently, or should we delete after a configurable period?
- Are there existing admin groups, or shall we create them with `Group` objects?
- Should the recording timer show elapsed time only, or also a “started at” timestamp?

---
## Proposed Changes
### 1. Backend – Models (`pms/models.py`)
```python
class Meetings(ChhabiModel):
    # existing fields …
    is_locked = models.BooleanField(default=False)
    allow_participant_video = models.BooleanField(default=True)
    allow_participant_audio = models.BooleanField(default=True)
    # Recording fields
    is_recording = models.BooleanField(default=False)
    recording_started_at = models.DateTimeField(null=True, blank=True)
    recording_ended_at = models.DateTimeField(null=True, blank=True)
    recording_file = models.FileField(upload_to='recordings/', null=True, blank=True)
    recording_duration = models.DurationField(null=True, blank=True)

class MeetingParticipant(models.Model):
    meeting = models.ForeignKey(Meetings, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    guest_name = models.CharField(max_length=150)
    role = models.CharField(max_length=20, choices=(('host','Host'),('admin','Admin'),('participant','Participant')))
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    is_video_enabled = models.BooleanField(default=True)
    is_audio_enabled = models.BooleanField(default=True)
    # additional fields for audit if needed
```
*No migrations are applied automatically in this plan; they will be generated once the plan is approved.*

### 2. Backend – Permissions (`pms/permissions.py`)
Create custom permissions:
- `meeting.can_admit`
- `meeting.can_remove`
- `meeting.can_lock`
- `meeting.can_manage_permissions`
- `meeting.can_record`
- `meeting.can_end`
Assign them to groups (`SuperAdmin`, `PlatformAdmin`, `OrgOwner`, `MeetingHost`). Use `user.has_perm('meeting.can_record', meeting)` in views.

### 3. Backend – Views (`pms/call_views.py`)
- **Host Join Logic**: After adding the user to `meeting.employee_id`, also create / update a `MeetingParticipant` entry and, if `can_control`, add to `meeting.manager`.
- **Lock/Unlock Endpoint**:
```python
@require_POST
@permission_required('meeting.can_lock')
def toggle_lock(request, room_code):
    meeting = get_object_or_404(Meetings, room_code=room_code)
    meeting.is_locked = not meeting.is_locked
    meeting.save()
    # broadcast signal
    MeetingSignal.objects.create(meeting=meeting, type='meeting_locked', payload={'locked': meeting.is_locked})
    return JsonResponse({'locked': meeting.is_locked})
```
- **Recording Endpoints** (`start_recording`, `stop_recording`):
```python
@require_POST
@permission_required('meeting.can_record')
def start_recording(request, room_code):
    meeting = get_object_or_404(Meetings, room_code=room_code)
    if meeting.is_recording:
        return JsonResponse({'error':'Already recording'}, status=400)
    meeting.is_recording = True
    meeting.recording_started_at = timezone.now()
    meeting.save()
    MeetingSignal.objects.create(meeting=meeting, type='recording_state', payload={'state':'started'})
    return JsonResponse({'started':True})

@require_POST
@permission_required('meeting.can_record')
def stop_recording(request, room_code):
    meeting = get_object_or_404(Meetings, room_code=room_code)
    if not meeting.is_recording:
        return JsonResponse({'error':'Not recording'}, status=400)
    meeting.is_recording = False
    meeting.recording_ended_at = timezone.now()
    meeting.recording_duration = meeting.recording_ended_at - meeting.recording_started_at
    # The actual media file will be uploaded by the client later via a separate endpoint.
    meeting.save()
    MeetingSignal.objects.create(meeting=meeting, type='recording_state', payload={'state':'stopped'})
    return JsonResponse({'stopped':True})
```
- **Upload Recording Endpoint** (`POST /meeting/<room_code>/recording/upload/`): Accept `multipart/form-data` with the recorded file; save to `meeting.recording_file`.
- **Signal Enhancements** (`meeting_signal`): Add new `type`s – `recording_state`, `participant_join`, `participant_leave`, `status_update`.
  - For host reconnection, ensure `recording_state` is sent if `meeting.is_recording`.

### 4. Frontend – UI (`pms/templates/meetings/call_room.html`)
- **Recording Banner**: Already present (`#recBanner`). Show when `meeting.is_recording` is true.
- **Timer**: Add JS timer that starts when `recording_state` ‑> `started` is received; stop on `stopped`. Use `setInterval` to update `#recTimer`.
- **Control Button** (`#btnRecord`):
  - If `IS_HOST` → clicking toggles start/stop via `fetch` to `/api/meetings/<room_code>/recording/start/` or `/stop/`.
  - Update button label/icon accordingly.
- **MediaRecorder Integration** (client‑side):
  ```javascript
  let recorder;
  let recordedChunks = [];
  async function startClientRecording() {
      const stream = new MediaStream();
      // combine local and remote tracks
      if (localStream) localStream.getTracks().forEach(t => stream.addTrack(t));
      Object.values(peers).forEach(p => {
          if (p.stream) p.stream.getTracks().forEach(t => stream.addTrack(t));
      });
      recorder = new MediaRecorder(stream, {mimeType:'video/webm'});
      recorder.ondataavailable = e => { if (e.data.size) recordedChunks.push(e.data); };
      recorder.start();
  }
  async function stopClientRecording() {
      recorder.stop();
      const blob = new Blob(recordedChunks, {type:'video/webm'});
      const form = new FormData();
      form.append('file', blob, `meeting_${room_code}.webm`);
      await fetch(`${base}recording/upload/`, {method:'POST', headers:{'X‑CSRFToken':csrf}, body:form});
      recordedChunks = [];
  }
  ```
  - Host initiates `startClientRecording()` when it receives the `recording_state: started` signal; participants may also start a local copy if desired (optional).
  - Ensure consent: the browser will automatically ask for permission to capture the screen/video/audio; do not mute/unmute without user action.
- **Participant List UI**: Extend the existing “Members” side panel to render each `MeetingParticipant` entry with:
  - Name (no email), role badge (Host/Admin), video/audio icons, join timestamp.
  - For host, add **Remove** button per row.
  - Use the existing polling loop (`meeting_signal` GET) to handle `participant_join`, `participant_leave`, `status_update` signals and update the DOM.

### 5. JavaScript – Signal Handling Updates
Add cases in the polling response processing:
```javascript
if (signal.type === 'recording_state') {
    const state = signal.payload.state;
    if (state === 'started') { showRecordingBanner(); startTimer(); if (IS_HOST) startClientRecording(); }
    else if (state === 'stopped') { hideRecordingBanner(); stopTimer(); if (IS_HOST) stopClientRecording(); }
}
if (signal.type === 'participant_join') { addParticipantToList(signal.payload); }
if (signal.type === 'participant_leave') { removeParticipantFromList(signal.payload.id); }
if (signal.type === 'status_update') { updateParticipantStatus(signal.payload); }
```
- The host will also broadcast `control` signals when performing mute/kick actions, which remain unchanged.

### 6. Tests (`pms/tests_meeting_recording.py`)
- **Permission Tests**: Verify only users with `meeting.can_record` can hit the start/stop endpoints (403 for others).
- **State Sync Tests**: Simulate a host starting a recording, then a participant fetching signals; ensure they receive `recording_state` and UI would show banner.
- **Timer Accuracy**: Use time mocking to assert that the recorded duration matches the elapsed time between start and stop.
- **Upload Test**: Post a small dummy video file to the upload endpoint and check that `meeting.recording_file` is set.
- **Reconnection Test**: After a simulated disconnect, ensure the participant still receives the current `recording_state` when they reconnect (the GET endpoint should include the latest state).

---
## Verification Plan
### Automated
1. Run `python manage.py test pms` – all new tests must pass.
2. Run `python manage.py check` – no configuration errors.
### Manual
1. Start the dev server.
2. Log in as a SuperAdmin (host) and create a meeting.
3. Verify the participant panel shows the host badge and counts.
4. Click **Record** – a banner appears, timer starts, and the host’s MediaRecorder begins.
5. Open a second browser as a normal participant – the banner appears synchronously, timer matches host.
6. Click **Lock** and attempt a new participant to join – they are prevented.
7. Test **Mute** and **Remove** controls – UI updates for all participants.
8. Stop recording – banner disappears, file is uploaded, and duration is stored.
9. Refresh/reconnect both host and participant – recording state persists correctly.
10. Attempt to start recording via API as a non‑host – expect `403 Forbidden`.

---
## Rollback Strategy
- All additions are additive; reverting involves removing the new fields, models, and view endpoints.
- No existing functionality is altered; existing URLs and templates remain untouched unless the new UI elements are disabled via a feature flag.
- Media files can be deleted without affecting the database.

*Implementation will commence after you approve this updated plan.*
