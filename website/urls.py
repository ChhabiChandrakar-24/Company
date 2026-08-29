from django.contrib.sitemaps.views import sitemap
from django.urls import path, include

from .sitemaps import PublicPageSitemap
from . import views
from . import api_views
from rest_framework.routers import DefaultRouter

SITEMAPS = {"public": PublicPageSitemap}

urlpatterns = [
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="django-contrib-sitemaps"),
    path("robots.txt", views.robots_txt, name="website-robots"),
    path("", views.public_page, {"slug": "home"}, name="website-home"),
    path("about/", views.public_page, {"slug": "about"}, name="website-about"),
    path("services/", views.public_page, {"slug": "services"}, name="website-services"),
    path("pricing/", views.public_page, {"slug": "pricing"}, name="website-pricing"),
    path("career/", views.public_page, {"slug": "career"}, name="website-career"),
    path("contact/", views.public_page, {"slug": "contact"}, name="website-contact"),
    path("faq/", views.public_page, {"slug": "faq"}, name="website-faq"),
    path("team/", views.public_page, {"slug": "team"}, name="website-team"),
    path("projects/", views.public_page, {"slug": "projects"}, name="website-projects"),
    path("privacy-policy/", views.public_page, {"slug": "privacy-policy"}, name="website-privacy"),
    path("terms-and-conditions/", views.public_page, {"slug": "terms-and-conditions"}, name="website-terms"),
    path("terms-conditions/", views.public_page, {"slug": "terms-conditions"}, name="website-terms-conditions"),
    path("thank-you/", views.public_page, {"slug": "thank-you"}, name="website-thank-you"),
    path("website/preview/<int:pk>/", views.preview_page, name="website-preview"),
    path("website/submit/", views.submit, name="website-submit"),
    path("search/", views.public_search, name="website-search"),
]

router = DefaultRouter()
router.register(r"pages", api_views.WebsitePageViewSet)
router.register(r"sections", api_views.WebsiteSectionViewSet)
router.register(r"navigation-menus", api_views.NavigationMenuViewSet)
router.register(r"navigation-items", api_views.NavigationItemViewSet)
router.register(r"settings", api_views.WebsiteSettingsViewSet)
router.register(r"themes", api_views.ThemeSettingsViewSet)
router.register(r"media", api_views.MediaAssetViewSet)

urlpatterns += [
    path("api/v1/cms/", include(router.urls)),
]
