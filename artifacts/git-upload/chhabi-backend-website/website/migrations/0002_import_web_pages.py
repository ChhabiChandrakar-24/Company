from pathlib import Path

from django.conf import settings
from django.db import migrations


PAGES = (
    ("home", "Home", "index.html", 0),
    ("about", "About Us", "about.html", 10),
    ("services", "Services", "services.html", 20),
    ("pricing", "Pricing Plan", "pricing.html", 30),
    ("career", "Careers", "career.html", 40),
    ("contact", "Contact Us", "contact.html", 50),
    ("faq", "FAQ", "faq.html", 60),
    ("team", "Our Team", "our-team.html", 70),
    ("projects", "Projects", "project.html", 80),
    ("thank-you", "Thank You", "thankyou.html", 90),
)


def import_pages(apps, schema_editor):
    WebsitePage = apps.get_model("website", "WebsitePage")
    web_dir = Path(settings.BASE_DIR) / "web"
    for slug, title, filename, order in PAGES:
        source = web_dir / filename
        if source.exists():
            WebsitePage.objects.get_or_create(
                slug=slug,
                defaults={
                    "title": title,
                    "html_content": source.read_text(encoding="utf-8", errors="replace"),
                    "navigation_order": order,
                    "show_in_navigation": slug != "thank-you",
                },
            )

class Migration(migrations.Migration):
    dependencies = [("website", "0001_initial")]
    operations = [migrations.RunPython(import_pages, migrations.RunPython.noop)]
