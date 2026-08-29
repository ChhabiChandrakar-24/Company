"""Sitemaps for public, indexable website pages."""

from django.contrib.sitemaps import Sitemap

from .models import WebsitePage


# Keep conversion and form-confirmation pages out of search results.
PUBLIC_PAGE_PATHS = {
    "home": "/",
    "about": "/about/",
    "services": "/services/",
    "pricing": "/pricing/",
    "career": "/career/",
    "contact": "/contact/",
    "faq": "/faq/",
    "team": "/team/",
    "projects": "/projects/",
    "terms-and-conditions": "/terms-and-conditions/",
}


class PublicPageSitemap(Sitemap):
    """Expose only public marketing pages and their CMS update dates."""

    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return list(PUBLIC_PAGE_PATHS)

    def location(self, slug):
        return PUBLIC_PAGE_PATHS[slug]

    def lastmod(self, slug):
        return (
            WebsitePage.objects.filter(slug=slug, status='published')
            .values_list("updated_at", flat=True)
            .first()
        )

    def priority(self, slug):
        return 1.0 if slug == "home" else 0.7
