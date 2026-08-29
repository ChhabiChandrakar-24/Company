from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from .models import MeetingCaption, MeetingMessage, MeetingNote, MeetingRecording, Meetings
from .meeting_providers import provision_external_meeting


class MeetingSerializer(serializers.ModelSerializer):
    join_url = serializers.SerializerMethodField()

    class Meta:
        model = Meetings
        fields = (
            "id", "title", "description", "date", "end_date", "meeting_type",
            "provider", "external_url", "room_code", "status", "allow_chat",
            "allow_captions", "allow_recording", "employee_id", "manager",
            "company_id", "join_url",
        )
        read_only_fields = ("room_code", "company_id")

    def get_join_url(self, obj):
        request = self.context.get("request")
        path = f"/pms/meeting-call/{obj.room_code}/"
        return request.build_absolute_uri(path) if request else path

    def create(self, validated_data):
        request = self.context["request"]
        employee = getattr(request.user, "employee_get", None)
        company = getattr(getattr(employee, "employee_work_info", None), "company_id", None)
        validated_data["company_id"] = company
        return super().create(validated_data)


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()

    class Meta:
        model = MeetingMessage
        fields = ("id", "meeting", "sender", "sender_name", "message", "created_at")
        read_only_fields = ("sender", "created_at")

    def get_sender_name(self, obj):
        return obj.sender.get_full_name() or obj.sender.username


class CaptionSerializer(serializers.ModelSerializer):
    speaker_name = serializers.SerializerMethodField()

    class Meta:
        model = MeetingCaption
        fields = ("id", "meeting", "speaker", "speaker_name", "text", "language", "created_at")
        read_only_fields = ("speaker", "created_at")

    def get_speaker_name(self, obj):
        return obj.speaker.get_full_name() or obj.speaker.username


class RecordingSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetingRecording
        fields = ("id", "meeting", "recorded_by", "file", "duration_seconds", "created_at")
        read_only_fields = ("recorded_by", "created_at")


class NoteSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = MeetingNote
        fields = ("id", "meeting", "author", "author_name", "note", "created_at")
        read_only_fields = ("author", "created_at")

    def get_author_name(self, obj):
        return obj.author.get_full_name() or obj.author.username


class MeetingViewSet(viewsets.ModelViewSet):
    serializer_class = MeetingSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        qs = Meetings.objects.all().order_by("-date", "-id")
        if user.is_superuser or user.has_perm("pms.manage_meeting_integrations"):
            return qs
        employee = getattr(user, "employee_get", None)
        return qs.filter(employee_id=employee) | qs.filter(manager=employee)

    def perform_create(self, serializer):
        if not self.request.user.has_perm("pms.add_meetings"):
            raise PermissionDenied("Meeting creation permission required")
        serializer.save()

    def perform_update(self, serializer):
        if not self.request.user.has_perm("pms.change_meetings"):
            raise PermissionDenied("Meeting change permission required")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.has_perm("pms.delete_meetings"):
            raise PermissionDenied("Meeting deletion permission required")
        instance.delete()

    @action(detail=True, methods=("post",))
    def provision(self, request, pk=None):
        if not request.user.has_perm("pms.manage_meeting_integrations"):
            return Response({"detail": "Integration permission required"}, status=403)
        meeting = self.get_object()
        provider = request.data.get("provider")
        try:
            meeting.external_url = provision_external_meeting(meeting, provider)
            meeting.provider, meeting.meeting_type = provider, "external"
            meeting.save()
            return Response(MeetingSerializer(meeting, context={"request": request}).data)
        except Exception as exc:
            return Response({"detail": str(exc)}, status=400)

    @action(detail=True, methods=("get", "post"))
    def messages(self, request, pk=None):
        meeting = self.get_object()
        if request.method == "POST":
            serializer = MessageSerializer(data={**request.data, "meeting": meeting.pk})
            serializer.is_valid(raise_exception=True)
            serializer.save(sender=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(MessageSerializer(meeting.call_messages.select_related("sender"), many=True).data)

    @action(detail=True, methods=("get", "post"))
    def captions(self, request, pk=None):
        meeting = self.get_object()
        if request.method == "POST":
            serializer = CaptionSerializer(data={**request.data, "meeting": meeting.pk})
            serializer.is_valid(raise_exception=True)
            serializer.save(speaker=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(CaptionSerializer(meeting.captions.select_related("speaker"), many=True).data)

    @action(detail=True, methods=("get", "post"))
    def notes(self, request, pk=None):
        meeting = self.get_object()
        if request.method == "POST":
            serializer = NoteSerializer(data={**request.data, "meeting": meeting.pk})
            serializer.is_valid(raise_exception=True)
            serializer.save(author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(NoteSerializer(meeting.notes.select_related("author"), many=True).data)

    @action(detail=True, methods=("get", "post", "delete"))
    def recordings(self, request, pk=None):
        meeting = self.get_object()
        if request.method == "DELETE":
            if not request.user.has_perm("pms.delete_meetingrecording"):
                return Response({"detail": "Recording deletion permission required"}, status=403)
            item = meeting.recordings.filter(pk=request.data.get("recording_id")).first()
            if not item:
                return Response({"detail": "Recording not found"}, status=404)
            try:
                item.file.delete(save=False)
            except PermissionError:
                return Response({"detail": "Recording is currently being downloaded. Retry after it closes."}, status=409)
            item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        if request.method == "POST":
            if not request.user.has_perm("pms.record_meeting_call"):
                return Response({"detail": "Recording permission required"}, status=403)
            serializer = RecordingSerializer(data={**request.data, "meeting": meeting.pk})
            serializer.is_valid(raise_exception=True)
            serializer.save(recorded_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(RecordingSerializer(meeting.recordings.all(), many=True, context={"request": request}).data)
