"""Seed SEO metadata (title, keywords, description) for public website pages.

Idempotent data migration: only fills fields that are still blank, so any
content edited later by an admin is never overwritten.
"""

from django.db import migrations

SEED = {
    "home": {
        "seo_title": "Geeta ForgeTech | Secure Software, Websites & IT Solutions",
        "focus_keyword": "software company noida",
        "additional_keywords": "IT services, web development, cyber security, mobile apps, cloud solutions",
        "meta_description": "Geeta ForgeTech delivers secure software, websites, mobile apps, cloud and 24/7 cyber security solutions for growing businesses in India.",
    },
    "about": {
        "seo_title": "About Us | Geeta ForgeTech",
        "focus_keyword": "about geeta forgetech",
        "additional_keywords": "IT company, software partner, our story, our team",
        "meta_description": "Learn about Geeta ForgeTech - a full-cycle software and cyber security company helping businesses grow with secure, modern technology.",
    },
    "services": {
        "seo_title": "Our Services | Geeta ForgeTech",
        "focus_keyword": "IT services company",
        "additional_keywords": "software development, cyber security services, cloud, web design",
        "meta_description": "Explore Geeta ForgeTech services: software development, websites, mobile apps, cloud migration and 24/7 cyber security operations.",
    },
    "pricing": {
        "seo_title": "Pricing Plans | Geeta ForgeTech",
        "focus_keyword": "IT services pricing",
        "additional_keywords": "software project cost, cyber security pricing, plans",
        "meta_description": "Transparent pricing plans for software, websites and cyber security services from Geeta ForgeTech. No hidden costs, scalable options.",
    },
    "career": {
        "seo_title": "Careers | Geeta ForgeTech",
        "focus_keyword": "IT jobs noida",
        "additional_keywords": "careers, openings, software jobs, cyber security jobs",
        "meta_description": "Join Geeta ForgeTech - open roles in software engineering, cyber security and design. Grow your career with a modern IT company.",
    },
    "contact": {
        "seo_title": "Contact Us | Geeta ForgeTech",
        "focus_keyword": "contact IT company",
        "additional_keywords": "get a quote, office noida, reach us",
        "meta_description": "Contact Geeta ForgeTech for a free consultation on software, websites and cyber security. Sector 62, Noida - call or email us today.",
    },
    "faq": {
        "seo_title": "FAQ | Geeta ForgeTech",
        "focus_keyword": "IT services faq",
        "additional_keywords": "questions, help, support",
        "meta_description": "Frequently asked questions about Geeta ForgeTech services, pricing, timelines and support. Get the answers you need fast.",
    },
    "team": {
        "seo_title": "Our Team | Geeta ForgeTech",
        "focus_keyword": "IT company team",
        "additional_keywords": "leadership, engineers, experts",
        "meta_description": "Meet the Geeta ForgeTech team - engineers, designers and cyber security experts who deliver secure, modern technology.",
    },
    "projects": {
        "seo_title": "Our Projects | Geeta ForgeTech",
        "focus_keyword": "software projects portfolio",
        "additional_keywords": "case studies, work, portfolio",
        "meta_description": "See selected projects delivered by Geeta ForgeTech across web, mobile and enterprise platforms with measurable results.",
    },
    "terms-and-conditions": {
        "seo_title": "Terms and Conditions | Geeta ForgeTech",
        "focus_keyword": "terms and conditions",
        "additional_keywords": "legal, website terms",
        "meta_description": "Terms and conditions governing use of our website and services.",
    },
    "thank-you": {
        "seo_title": "Thank You | Geeta ForgeTech",
        "focus_keyword": "thank you",
        "additional_keywords": "submission received",
        "meta_description": "Thank you for contacting Geeta ForgeTech. We will get back to you shortly.",
    },
}

DEFAULT_KEYWORDS = (
    "software development, web design, cyber security, mobile apps, cloud, "
    "IT services, Geeta ForgeTech, Noida"
)


def seed_seo(apps, schema_editor):
    WebsitePage = apps.get_model("website", "WebsitePage")
    WebsiteSettings = apps.get_model("website", "WebsiteSettings")
    for slug, data in SEED.items():
        page = WebsitePage.objects.filter(slug=slug).first()
        if page is None:
            continue
        for field, value in data.items():
            if not getattr(page, field):
                setattr(page, field, value)
        page.save(update_fields=list(data.keys()))
    settings = WebsiteSettings.objects.first()
    if settings and not settings.default_meta_keywords:
        settings.default_meta_keywords = DEFAULT_KEYWORDS
        settings.save(update_fields=["default_meta_keywords"])


def unseed_seo(apps, schema_editor):
    # Reverse is a no-op: we never delete admin-edited SEO content.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0019_premium_content_seed"),
    ]

    operations = [
        migrations.RunPython(seed_seo, unseed_seo),
    ]
