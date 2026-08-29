from rest_framework import serializers
from .models import WebsiteScan

class WebsiteScanHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = WebsiteScan
        fields = ('id', 'status', 'started_at', 'completed_at', 'overall_score', 'seo_score', 'aeo_score', 'geo_score', 'llmo_score', 'eeat_score')
