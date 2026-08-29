from rest_framework import viewsets, status
from rest_framework.permissions import IsAdminUser
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import (
    WebsitePage, WebsiteSection, NavigationMenu, NavigationItem, 
    WebsiteSettings, ThemeSettings, MediaAsset
)
from .serializers import (
    WebsitePageSerializer, WebsiteSectionSerializer, NavigationMenuSerializer, 
    NavigationItemSerializer, WebsiteSettingsSerializer, ThemeSettingsSerializer, 
    MediaAssetSerializer
)

class WebsitePageViewSet(viewsets.ModelViewSet):
    queryset = WebsitePage.objects.all()
    serializer_class = WebsitePageSerializer
    permission_classes = [IsAdminUser]

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        page = self.get_object()
        page.status = 'published'
        page.save()
        return Response({'status': 'page published'})

    @action(detail=True, methods=['post'])
    def unpublish(self, request, pk=None):
        page = self.get_object()
        page.status = 'draft'
        page.save()
        return Response({'status': 'page unpublished'})


class WebsiteSectionViewSet(viewsets.ModelViewSet):
    queryset = WebsiteSection.objects.all()
    serializer_class = WebsiteSectionSerializer
    permission_classes = [IsAdminUser]


class NavigationMenuViewSet(viewsets.ModelViewSet):
    queryset = NavigationMenu.objects.all()
    serializer_class = NavigationMenuSerializer
    permission_classes = [IsAdminUser]


class NavigationItemViewSet(viewsets.ModelViewSet):
    queryset = NavigationItem.objects.all()
    serializer_class = NavigationItemSerializer
    permission_classes = [IsAdminUser]


class WebsiteSettingsViewSet(viewsets.ModelViewSet):
    queryset = WebsiteSettings.objects.all()
    serializer_class = WebsiteSettingsSerializer
    permission_classes = [IsAdminUser]


class ThemeSettingsViewSet(viewsets.ModelViewSet):
    queryset = ThemeSettings.objects.all()
    serializer_class = ThemeSettingsSerializer
    permission_classes = [IsAdminUser]


class MediaAssetViewSet(viewsets.ModelViewSet):
    queryset = MediaAsset.objects.all()
    serializer_class = MediaAssetSerializer
    permission_classes = [IsAdminUser]
