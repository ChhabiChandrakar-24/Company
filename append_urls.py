
import re

content = open("website/urls.py", encoding="utf-8").read()

if "api_views" not in content:
    content = content.replace("from . import views", "from . import views\nfrom . import api_views\nfrom rest_framework.routers import DefaultRouter")

    router_code = """
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
"""
    
    # We also need to import include if not there
    if "include" not in content:
        content = content.replace("from django.urls import path", "from django.urls import path, include")
        
    content += router_code
    
    with open("website/urls.py", "w", encoding="utf-8") as f:
        f.write(content)
print("URLs updated.")

