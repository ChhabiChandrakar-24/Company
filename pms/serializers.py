from rest_framework import serializers
from .models import MeetingMessage, MeetingNote, MeetingInvitation, Meetings

class MeetingChatMessageSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MeetingMessage
        fields = ["id", "meeting", "author", "author_name", "content", "timestamp"]
        read_only_fields = ["id", "timestamp", "author_name"]

    def get_author_name(self, obj):
        return obj.author.get_full_name() or obj.author.username

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["author"] = request.user
        return super().create(validated_data)

class MeetingNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MeetingNote
        fields = ["id", "meeting", "author", "author_name", "content", "is_shared", "timestamp"]
        read_only_fields = ["id", "timestamp", "author_name"]

    def get_author_name(self, obj):
        return obj.author.get_full_name() or obj.author.username

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["author"] = request.user
        return super().create(validated_data)

class MeetingInvitationSerializer(serializers.ModelSerializer):
    join_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MeetingInvitation
        fields = ["id", "meeting", "token", "expires_at", "revoked", "password", "waiting_room", "join_url"]
        read_only_fields = ["id", "token", "join_url"]

    def get_join_url(self, obj):
        request = self.context.get("request")
        if request:
            from django.urls import reverse
            return request.build_absolute_uri(reverse("pms:meeting-invitation-join", args=[obj.meeting.id, obj.token]))
        return None

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["created_by"] = user
        import secrets
        validated_data["token"] = secrets.token_urlsafe(32)
        return super().create(validated_data)

# Fix MeetingNoteSerializer field names
class MeetingNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MeetingNote
        fields = ["id", "meeting", "author", "author_name", "note", "created_at"]
        read_only_fields = ["id", "created_at", "author_name"]

    def get_author_name(self, obj):
        return obj.author.get_full_name() or obj.author.username

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["author"] = request.user
        return super().create(validated_data)

class CaptionToggleSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
