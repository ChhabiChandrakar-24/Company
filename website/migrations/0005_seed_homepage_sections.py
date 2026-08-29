from django.db import migrations


SECTIONS = (
    ("hero", "Secure Software, Websites & IT Solutions You Can Trust", "We build secure software and websites backed by expert cybersecurity — empowering your business to grow with confidence and safety.", [{"title": "Get Started", "url": "/about/"}, {"title": "Contact us", "url": "/contact/"}]),
    ("about", "24/7 Cyber Security Operation Center", "We monitor, detect and respond to threats in real time, keeping your software, websites, servers and cloud infrastructure protected.", [{"title": "Malware Detection"}, {"title": "Cloud Security"}, {"title": "Cyber Security"}, {"title": "Server Security"}]),
    ("who_we_are", "Who we are", "We are a dedicated team of cybersecurity and software experts delivering trusted, innovative and scalable technology solutions.", [{"title": "2K+", "description": "Engagements"}, {"title": "17M+", "description": "Monitored Globally"}, {"title": "18K+", "description": "Network Sensors"}]),
    ("what_we_do", "What we do", "Tailored solutions for cybersecurity, digital transformation and enterprise automation.", [{"title": "Cyber Solutions", "description": "Comprehensive defence systems for your data and networks."}, {"title": "Network Security", "description": "Advanced monitoring and firewall implementation."}, {"title": "Web Security", "description": "Secure development and malware protection."}]),
    ("testimonials", "Clients Trust Us for a Reason", "Our clients value clear communication, dependable delivery and secure solutions.", [{"title": "Rahul Mehta", "description": "The team was professional, responsive and delivered beyond our expectations."}, {"title": "Ananya Sharma", "description": "Our system is now more secure and efficient thanks to their expertise."}, {"title": "Vikram Raj", "description": "Every stage was handled with clarity, precision and a focus on quality."}]),
    ("get_started", "Get Started Now", "Send us a Message", []),
)


def seed_home(apps, schema_editor):
    WebsitePage = apps.get_model("website", "WebsitePage")
    WebsiteSection = apps.get_model("website", "WebsiteSection")
    home = WebsitePage.objects.filter(slug="home").first()
    if not home:
        return
    for order, (kind, heading, content, items) in enumerate(SECTIONS, 1):
        WebsiteSection.objects.update_or_create(
            page=home, section_type=kind,
            defaults={"heading": heading, "content": content, "items": items, "sort_order": order * 10, "is_active": True},
        )


class Migration(migrations.Migration):
    dependencies = [("website", "0004_seed_structured_website_content")]
    operations = [migrations.RunPython(seed_home, migrations.RunPython.noop)]
