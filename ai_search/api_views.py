from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import WebsiteScan, Website
from .serializers import WebsiteScanHistorySerializer
from django.shortcuts import get_object_or_404

class WebsiteScanHistoryAPI(generics.ListAPIView):
    serializer_class = WebsiteScanHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        website_id = self.kwargs.get('website_id')
        website = get_object_or_404(Website, id=website_id)
        # Ensure user has access (for now anyone authenticated can see, but could restrict to created_by)
        return WebsiteScan.objects.filter(website=website, status='completed').order_by('completed_at')
