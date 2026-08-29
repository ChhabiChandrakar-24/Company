
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chhabi.settings")
django.setup()

from django.conf import settings
if "testserver" not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append("testserver")

from rest_framework.test import APIClient
from django.contrib.auth.models import User
from website.models import WebsitePage, WebsiteSection

client = APIClient()

admin_user, _ = User.objects.get_or_create(username="cms_admin", is_staff=True, is_superuser=True)
if not admin_user.password:
    admin_user.set_password("adminpass")
    admin_user.save()

normal_user, _ = User.objects.get_or_create(username="normal_user")

print("Testing Unauthorized Access...")
resp = client.post("/api/v1/cms/pages/", {"title": "Test", "slug": "test"})
if resp.status_code in [401, 403]:
    print("SUCCESS: Unauthorized access blocked.")
else:
    print(f"FAILED: Expected 401/403, got {resp.status_code}")

client.force_authenticate(user=normal_user)
resp = client.post("/api/v1/cms/pages/", {"title": "Test", "slug": "test"})
if resp.status_code in [401, 403]:
    print("SUCCESS: Normal user access blocked.")
else:
    print(f"FAILED: Expected 401/403, got {resp.status_code}")

print("\nTesting Admin Access & Creation...")
client.force_authenticate(user=admin_user)
payload = {
    "title": "API Test Page",
    "slug": "api-test",
    "status": "draft",
    "seo_title": "Best Test Page",
    "html_content": "<p>Test Page</p>"
}
resp = client.post("/api/v1/cms/pages/", payload, format="json")
if resp.status_code == 201:
    print("SUCCESS: Admin created a test page.")
    page_id = resp.json()["id"]
else:
    print(f"FAILED: Admin could not create page. Status: {resp.status_code}, {resp.content}")
    exit(1)

print("\nTesting Section Addition...")
section_payload = {
    "page": page_id,
    "heading": "Welcome to API Test",
    "visibility": "public"
}
resp = client.post("/api/v1/cms/sections/", section_payload, format="json")
if resp.status_code == 201:
    print("SUCCESS: Section added to the page.")
else:
    print(f"FAILED: Could not add section. Status: {resp.status_code}, {resp.content}")

page = WebsitePage.objects.filter(id=page_id).first()
if page and page.sections.count() > 0:
    print("\nSUCCESS: Data saved in database correctly!")
else:
    print("\nFAILED: Data not found in database.")

if page:
    page.delete()
User.objects.filter(username__in=["cms_admin", "normal_user"]).delete()

