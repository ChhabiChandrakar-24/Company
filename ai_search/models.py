from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Website(models.Model):
    name = models.CharField(max_length=255)
    base_url = models.URLField(unique=True)
    organization_name = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=[('active', 'Active'), ('paused', 'Paused')], default='active')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='ai_search_websites')
    max_crawl_pages = models.IntegerField(default=10, help_text="Maximum number of pages to crawl per scan")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = [
            ("view_ai_search_dashboard", "Can view AI Search Dashboard"),
            ("start_scan", "Can start scan"),
            ("manage_recommendations", "Can manage recommendations"),
        ]

    def __str__(self):
        return f"{self.name} ({self.base_url})"

class WebsiteScan(models.Model):
    website = models.ForeignKey(Website, on_delete=models.CASCADE, related_name='scans')
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('running', 'Running'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    overall_score = models.IntegerField(null=True, blank=True)
    seo_score = models.IntegerField(null=True, blank=True)
    aeo_score = models.IntegerField(null=True, blank=True)
    geo_score = models.IntegerField(null=True, blank=True)
    llmo_score = models.IntegerField(null=True, blank=True)
    eeat_score = models.IntegerField(null=True, blank=True)
    
    def __str__(self):
        return f"Scan {self.id} for {self.website.name} ({self.status})"

class CrawledPage(models.Model):
    scan = models.ForeignKey(WebsiteScan, on_delete=models.CASCADE, related_name='pages')
    url = models.URLField(max_length=2000)
    status_code = models.IntegerField(null=True, blank=True)
    title = models.TextField(null=True, blank=True)
    meta_description = models.TextField(null=True, blank=True)
    canonical_url = models.URLField(max_length=2000, null=True, blank=True)
    robots_meta = models.CharField(max_length=255, null=True, blank=True)
    language = models.CharField(max_length=50, null=True, blank=True)
    h1_headings = models.JSONField(default=list)
    h2_headings = models.JSONField(default=list)
    h3_headings = models.JSONField(default=list)
    word_count = models.IntegerField(default=0)
    images_count = models.IntegerField(default=0)
    images_with_alt = models.IntegerField(default=0)
    internal_links_count = models.IntegerField(default=0)
    external_links_count = models.IntegerField(default=0)
    has_structured_data = models.BooleanField(default=False)
    raw_content = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.url

class AnalysisIssue(models.Model):
    scan = models.ForeignKey(WebsiteScan, on_delete=models.CASCADE, related_name='issues')
    page = models.ForeignKey(CrawledPage, on_delete=models.SET_NULL, null=True, blank=True, related_name='issues')
    title = models.CharField(max_length=255)
    description = models.TextField()
    severity = models.CharField(max_length=20, choices=[('critical', 'Critical'), ('high', 'High'), ('medium', 'Medium'), ('low', 'Low')])
    category = models.CharField(max_length=50, choices=[('seo', 'SEO'), ('aeo', 'AEO'), ('geo', 'GEO'), ('llmo', 'LLMO'), ('eeat', 'E-E-A-T')])
    status = models.CharField(max_length=20, choices=[('open', 'Open'), ('resolved', 'Resolved'), ('ignored', 'Ignored')], default='open')
    detected_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.get_severity_display()}] {self.title}"

class Recommendation(models.Model):
    issue = models.ForeignKey(AnalysisIssue, on_delete=models.CASCADE, related_name='recommendations')
    description = models.TextField()

    def __str__(self):
        return f"Recommendation for {self.issue.title}"
