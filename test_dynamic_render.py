
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chhabi.settings")
django.setup()

from django.test import RequestFactory
from website.models import WebsitePage, WebsiteSection

rf = RequestFactory()

# Clean up
WebsitePage.objects.filter(slug="dynamic-test").delete()

# Create dynamic test page
page = WebsitePage.objects.create(
    title="Dynamic Test Page",
    slug="dynamic-test",
    status="published",
    is_dynamic_render=True
)

WebsiteSection.objects.create(
    page=page,
    section_type="hero",
    heading="Welcome to Dynamic Hero",
    content="<p>This is a hero section.</p>",
    sort_order=1,
    visibility="public"
)

WebsiteSection.objects.create(
    page=page,
    section_type="text",
    heading="Dynamic Text Section",
    content="<p>This is standard text.</p>",
    sort_order=2,
    visibility="public"
)

# Render view directly
from website.views import public_page
from django.contrib.auth.models import AnonymousUser
request = rf.get("/dynamic-test/")
request.user = AnonymousUser()

try:
    response = public_page(request, slug="dynamic-test")
    html = response.content.decode("utf-8")
    
    if "Welcome to Dynamic Hero" in html and "Dynamic Text Section" in html:
        print("SUCCESS: Dynamic components rendered successfully!")
        
        # Check order
        hero_idx = html.find("Welcome to Dynamic Hero")
        text_idx = html.find("Dynamic Text Section")
        if hero_idx < text_idx:
            print("SUCCESS: Sections rendered in correct display order.")
        else:
            print("FAILED: Sections rendered in wrong order.")
    else:
        print("FAILED: Did not find section content in HTML.")
        print(html[:500])
except Exception as e:
    print(f"FAILED with Exception: {e}")

page.delete()

