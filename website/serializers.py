from rest_framework import serializers
from .models import (
    WebsitePage, WebsiteSection, NavigationMenu, NavigationItem, 
    WebsiteSettings, ThemeSettings, MediaAsset
)

class WebsiteSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebsiteSection
        fields = '__all__'

class WebsitePageSerializer(serializers.ModelSerializer):
    sections = WebsiteSectionSerializer(many=True, read_only=True)
    
    class Meta:
        model = WebsitePage
        fields = '__all__'

class NavigationItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = NavigationItem
        fields = '__all__'

    def validate(self, data):
        url = data.get('url')
        page = data.get('page')
        if not url and not page:
            raise serializers.ValidationError("Either a direct URL or a linked Page must be provided.")
        if page and page.status != 'published':
            raise serializers.ValidationError("Cannot link to an unpublished page.")
        return data

class NavigationMenuSerializer(serializers.ModelSerializer):
    items = NavigationItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = NavigationMenu
        fields = '__all__'

class WebsiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebsiteSettings
        fields = '__all__'

class ThemeSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ThemeSettings
        fields = '__all__'

class MediaAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaAsset
        fields = '__all__'
