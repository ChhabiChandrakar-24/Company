from django.contrib import admin
from .models import (
    FooterLink,
    FooterSection,
    FooterSocialLink,
    JobOpening,
    PricingPlan,
    TeamMember,
    WebsitePage,
    WebsiteSection,
    WebsiteService,
    WebsiteSettings,
    WebsiteSubmission,
)


admin.site.site_header = "Website Management"
admin.site.site_title = "Website Management"
admin.site.index_title = "Manage website content"


@admin.register(WebsiteSettings)
class WebsiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Company", {"fields": ("company_name", "tagline", "logo", "favicon", "footer_text")}),
        ("Contact", {"fields": ("phone", "email", "address")}),
        ("Social links", {"fields": ("facebook_url", "instagram_url", "linkedin_url", "twitter_url")}),
        ("Default SEO", {"fields": ("default_meta_description", "default_meta_keywords")}),
    )

    def has_add_permission(self, request):
        return not WebsiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(WebsitePage)
class WebsitePageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "is_published", "show_in_navigation", "updated_at")
    list_editable = ("is_published", "show_in_navigation")
    search_fields = ("title", "slug", "html_content")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(WebsiteSubmission)
class WebsiteSubmissionAdmin(admin.ModelAdmin):
    list_display = ("submission_type", "name", "email", "phone", "is_read", "created_at")
    list_filter = ("submission_type", "is_read", "created_at")
    search_fields = ("name", "email", "phone", "message")
    readonly_fields = ("submission_type", "name", "email", "phone", "message", "extra_data", "created_at")


class WebsiteSectionInline(admin.StackedInline):
    model = WebsiteSection
    extra = 0


WebsitePageAdmin.inlines = (WebsiteSectionInline,)


@admin.register(WebsiteSection)
class WebsiteSectionAdmin(admin.ModelAdmin):
    list_display = ("heading", "page", "section_type", "is_active", "sort_order")
    list_filter = ("page", "section_type", "is_active")
    list_editable = ("is_active", "sort_order")
    search_fields = ("heading", "subheading", "content")


@admin.register(WebsiteService)
class WebsiteServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "short_description", "full_description")


@admin.register(PricingPlan)
class PricingPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "billing_period", "is_featured", "is_active", "sort_order")
    list_editable = ("is_featured", "is_active", "sort_order")


@admin.register(JobOpening)
class JobOpeningAdmin(admin.ModelAdmin):
    list_display = ("title", "location", "job_type", "is_active", "sort_order")
    list_filter = ("job_type", "is_active")
    list_editable = ("is_active", "sort_order")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "location", "description", "requirements")


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ("name", "designation", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")
    search_fields = ("name", "designation", "bio")


class FooterLinkInline(admin.TabularInline):
    model = FooterLink
    extra = 1


@admin.register(FooterSection)
class FooterSectionAdmin(admin.ModelAdmin):
    list_display = ("title", "section_type", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")
    list_filter = ("section_type", "is_active")
    inlines = (FooterLinkInline,)


@admin.register(FooterLink)
class FooterLinkAdmin(admin.ModelAdmin):
    list_display = ("label", "section", "url", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")
    list_filter = ("section", "is_active")
    search_fields = ("label", "url")


@admin.register(FooterSocialLink)
class FooterSocialLinkAdmin(admin.ModelAdmin):
    list_display = ("platform", "url", "icon_class", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")
