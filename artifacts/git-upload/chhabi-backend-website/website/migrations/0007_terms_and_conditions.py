from pathlib import Path

from django.conf import settings
from django.db import migrations


def add_terms_page_and_footer_link(apps, schema_editor):
    WebsitePage = apps.get_model("website", "WebsitePage")
    FooterSection = apps.get_model("website", "FooterSection")
    FooterLink = apps.get_model("website", "FooterLink")
    source = Path(settings.BASE_DIR) / "web" / "terms-and-conditions.html"
    WebsitePage.objects.update_or_create(
        slug="terms-and-conditions",
        defaults={
            "title": "Terms & Conditions",
            "meta_description": "Terms and conditions governing use of our website and services.",
            "html_content": source.read_text(encoding="utf-8", errors="replace"),
            "is_published": True,
            "show_in_navigation": True,
            "navigation_order": 90,
        },
    )
    legal, _ = FooterSection.objects.get_or_create(
        title="Legal",
        defaults={"section_type": "links", "sort_order": 40, "is_active": True},
    )
    FooterLink.objects.update_or_create(
        section=legal,
        label="Terms & Conditions",
        defaults={"url": "/terms-and-conditions/", "sort_order": 10, "is_active": True},
    )


class Migration(migrations.Migration):
    dependencies = [("website", "0006_dynamic_footer")]
    operations = [migrations.RunPython(add_terms_page_and_footer_link, migrations.RunPython.noop)]
