
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chhabi.settings")
django.setup()

from django.test import Client
from website.models import WebsitePage, NavigationMenu, NavigationItem, WebsiteSettings

client = Client()

# Clean up
WebsitePage.objects.filter(slug="nav-test").delete()
NavigationMenu.objects.filter(slug__in=["main", "footer"]).delete()
WebsiteSettings.objects.all().delete()

# Create dynamic test page
page = WebsitePage.objects.create(
    title="Nav Test Page",
    slug="nav-test",
    status="published",
    is_dynamic_render=True
)

# Settings
WebsiteSettings.objects.create(
    company_name="Dynamic Nav Company",
    footer_text="Footer Works Dynamically"
)

# Menus
main_menu = NavigationMenu.objects.create(name="Main Menu", slug="main")
footer_menu = NavigationMenu.objects.create(name="Footer Menu", slug="footer")

# Main Menu Items
parent_item = NavigationItem.objects.create(menu=main_menu, label="Parent Dropdown", url="#", sort_order=1)
NavigationItem.objects.create(menu=main_menu, label="Child Page", url="/child-page/", parent=parent_item, sort_order=1)
NavigationItem.objects.create(menu=main_menu, label="Root Page", url="/root-page/", sort_order=2)

# Footer Menu Items
NavigationItem.objects.create(menu=footer_menu, label="Privacy Policy", url="/privacy/", sort_order=1)

try:
    response = client.get("/nav-test/")
    if response.status_code == 200:
        html = response.content.decode("utf-8")
        
        checks = [
            ("Dynamic Nav Company", "Company Name rendered"),
            ("Footer Works Dynamically", "Footer Text rendered"),
            ("Parent Dropdown", "Parent Dropdown rendered"),
            ("Child Page", "Child Page rendered"),
            ("Root Page", "Root Page rendered"),
            ("Privacy Policy", "Privacy Policy rendered"),
        ]
        
        all_passed = True
        for string, desc in checks:
            if string in html:
                print(f"SUCCESS: {desc}")
            else:
                print(f"FAILED: {desc} - Not found in HTML")
                all_passed = False
                
        if all_passed:
            print("ALL NAVIGATION TESTS PASSED!")
    else:
        print(f"FAILED: Request returned status {response.status_code}")
except Exception as e:
    print(f"FAILED with Exception: {e}")

page.delete()
main_menu.delete()
footer_menu.delete()
WebsiteSettings.objects.all().delete()

