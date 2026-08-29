from django.db import migrations


def seed_content(apps, schema_editor):
    WebsiteSettings = apps.get_model("website", "WebsiteSettings")
    WebsiteService = apps.get_model("website", "WebsiteService")
    PricingPlan = apps.get_model("website", "PricingPlan")
    JobOpening = apps.get_model("website", "JobOpening")
    TeamMember = apps.get_model("website", "TeamMember")
    WebsiteSection = apps.get_model("website", "WebsiteSection")
    WebsitePage = apps.get_model("website", "WebsitePage")
    WebsiteSettings.objects.get_or_create(pk=1, defaults={"company_name": "Geeta Forgetech", "tagline": "Technology that moves your business forward", "phone": "+91 8819981884", "email": "chcyberarmy@gmail.com", "footer_text": "Digital products, platforms and technology services."})
    for order, (name, slug, description) in enumerate((("Web Development", "web-development", "Responsive, secure and maintainable web platforms."), ("Mobile Applications", "mobile-applications", "Cross-platform mobile experiences for customers and teams."), ("Cloud & DevOps", "cloud-devops", "Reliable cloud infrastructure, automation and monitoring."))):
        WebsiteService.objects.get_or_create(slug=slug, defaults={"name": name, "short_description": description, "full_description": description, "sort_order": order})
    for order, (name, price, features) in enumerate((("Starter", 24999, "Responsive website\nContact forms\nBasic support"), ("Business", 59999, "Custom workflows\nAdmin dashboard\nPriority support"), ("Enterprise", 149999, "Solution architecture\nIntegrations\nDedicated support"))):
        PricingPlan.objects.get_or_create(name=name, defaults={"price": price, "billing_period": "project", "description": "A flexible starting point for your project.", "features": features, "is_featured": name == "Business", "sort_order": order})
    JobOpening.objects.get_or_create(slug="full-stack-developer", defaults={"title": "Full Stack Developer", "location": "India / Remote", "job_type": "Full Time", "experience": "2+ years", "description": "Build and maintain modern web applications.", "requirements": "Strong Python or PHP, JavaScript and database fundamentals.", "application_email": "careers@geetaforgetech.com"})
    TeamMember.objects.get_or_create(name="Geeta Forgetech Team", defaults={"designation": "Technology & Delivery", "bio": "A multidisciplinary team focused on customer outcomes."})
    about = WebsitePage.objects.filter(slug="about").first()
    if about:
        for order, (kind, heading, content) in enumerate((("mission", "Our Mission", "Make dependable technology accessible to ambitious organisations."), ("vision", "Our Vision", "Be the trusted digital partner behind meaningful growth."), ("values", "Our Values", "Integrity, ownership, craftsmanship and customer success.")), 1):
            WebsiteSection.objects.get_or_create(page=about, section_type=kind, defaults={"heading": heading, "content": content, "sort_order": order * 10})


class Migration(migrations.Migration):
    dependencies = [("website", "0003_structured_website_content")]
    operations = [migrations.RunPython(seed_content, migrations.RunPython.noop)]
