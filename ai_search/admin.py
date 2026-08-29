from django.contrib import admin
from .models import Website, WebsiteScan, CrawledPage, AnalysisIssue, Recommendation

@admin.register(Website)
class WebsiteAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_url', 'status', 'created_by', 'created_at')
    search_fields = ('name', 'base_url', 'organization_name')
    list_filter = ('status',)

@admin.register(WebsiteScan)
class WebsiteScanAdmin(admin.ModelAdmin):
    list_display = ('website', 'status', 'started_at', 'overall_score')
    list_filter = ('status',)

@admin.register(CrawledPage)
class CrawledPageAdmin(admin.ModelAdmin):
    list_display = ('url', 'scan', 'status_code')
    search_fields = ('url', 'title')

@admin.register(AnalysisIssue)
class AnalysisIssueAdmin(admin.ModelAdmin):
    list_display = ('title', 'severity', 'category', 'status', 'scan')
    list_filter = ('severity', 'category', 'status')
    search_fields = ('title', 'description')

@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ('issue', 'description')
