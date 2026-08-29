from django.contrib import admin
from .models import (
    WebsiteSettings,
    WebsitePage,
    WebsiteSection,
    WebsiteService,
    PricingPlan,
    JobOpening,
    TeamMember,
    FooterSection,
    FooterLink,
    FooterSocialLink,
    WebsiteSubmission,
    PortfolioProject,
    Testimonial,
    FAQ,
    WebsiteSectionItem,
    NavigationMenu,
    NavigationItem,
    ThemeSettings,
    MediaAsset,
    WebsiteProduct,
    CarouselSlide,
)

class WebsiteSectionItemInline(admin.TabularInline):
    model = WebsiteSectionItem
    extra = 0
    fields = ("title", "subtitle", "description", "value", "image", "icon", "button_text", "button_url", "sort_order", "is_active")

class WebsiteSectionInline(admin.TabularInline):
    model = WebsiteSection
    extra = 1
    fields = ("section_type", "heading", "subheading", "content", "image", "is_active", "sort_order")
    readonly_fields = []
    show_change_link = True

@admin.register(WebsitePage)
class WebsitePageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "status", "show_in_navigation", "navigation_order", "updated_at")
    list_filter = ("status", "show_in_navigation")
    search_fields = ("title", "slug")
    ordering = ("navigation_order", "title")
    inlines = [WebsiteSectionInline]
    actions = ["preview_page_action"]

    def preview_page_action(self, request, queryset):
        """Admin action that redirects to the staff preview page for the first selected page."""
        if queryset.count() == 1:
            page = queryset.first()
            return admin.redirect_to(f"/website/preview/{page.pk}/")
        self.message_user(request, "Select a single page to preview.")
    preview_page_action.short_description = "Preview selected page"

@admin.register(WebsiteSettings)
class WebsiteSettingsAdmin(admin.ModelAdmin):
    list_display = ("company_name", "phone", "email")
    readonly_fields = ("company_name",)

@admin.register(WebsiteSection)
class WebsiteSectionAdmin(admin.ModelAdmin):
    list_display = ("heading", "page", "section_type", "is_active", "sort_order")
    list_filter = ("page", "section_type", "is_active")
    list_editable = ("is_active", "sort_order")
    exclude = ("items", "settings")
    inlines = (WebsiteSectionItemInline,)

admin.site.register(WebsiteService)
admin.site.register(PricingPlan)
admin.site.register(JobOpening)
admin.site.register(TeamMember)
admin.site.register(FooterSection)
admin.site.register(FooterLink)
admin.site.register(FooterSocialLink)
admin.site.register(WebsiteSubmission)
admin.site.register(PortfolioProject)
admin.site.register(Testimonial)
admin.site.register(FAQ)
admin.site.register(WebsiteSectionItem)
admin.site.register(NavigationMenu)
admin.site.register(NavigationItem)
admin.site.register(ThemeSettings)
admin.site.register(MediaAsset)
admin.site.register(WebsiteProduct)
admin.site.register(CarouselSlide)
