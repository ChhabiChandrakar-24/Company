from django.db import migrations, models
import django.db.models.deletion


def seed_footer(apps, schema_editor):
    FooterSection = apps.get_model("website", "FooterSection")
    FooterLink = apps.get_model("website", "FooterLink")
    FooterSocialLink = apps.get_model("website", "FooterSocialLink")
    about = FooterSection.objects.create(title="About Us", section_type="links", sort_order=10)
    for order, (label, url) in enumerate((("Services", "/services/"), ("Projects", "/projects/"), ("Careers", "/career/"), ("About Us", "/about/"), ("Pricing Plan", "/pricing/"), ("Contact Us", "/contact/")), 1):
        FooterLink.objects.create(section=about, label=label, url=url, sort_order=order)
    FooterSection.objects.create(title="Contact Info", section_type="contact", sort_order=20)
    FooterSection.objects.create(title="Sign up for Newsletter", section_type="newsletter", content="Get company news and useful updates.", sort_order=30)
    for order, (platform, url, icon) in enumerate((("Facebook", "https://facebook.com/", "fa-brands fa-facebook-f"), ("Instagram", "https://instagram.com/", "fa-brands fa-instagram"), ("LinkedIn", "https://linkedin.com/", "fa-brands fa-linkedin-in")), 1):
        FooterSocialLink.objects.create(platform=platform, url=url, icon_class=icon, sort_order=order)


class Migration(migrations.Migration):
    dependencies = [("website", "0005_seed_homepage_sections")]
    operations = [
        migrations.CreateModel(name="FooterSection", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("title", models.CharField(max_length=150)), ("section_type", models.CharField(choices=[("links", "Links"), ("text", "Text"), ("contact", "Contact information"), ("newsletter", "Newsletter form")], default="links", max_length=20)), ("content", models.TextField(blank=True, help_text="Optional text shown inside this footer section.")), ("sort_order", models.PositiveIntegerField(default=0)), ("is_active", models.BooleanField(default=True))], options={"ordering": ("sort_order", "id")}),
        migrations.CreateModel(name="FooterSocialLink", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("platform", models.CharField(max_length=80)), ("url", models.URLField()), ("icon_class", models.CharField(default="fa-solid fa-link", max_length=100)), ("sort_order", models.PositiveIntegerField(default=0)), ("is_active", models.BooleanField(default=True))], options={"ordering": ("sort_order", "id")}),
        migrations.CreateModel(name="FooterLink", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("label", models.CharField(max_length=120)), ("url", models.CharField(help_text="Internal path, email, phone or full URL.", max_length=500)), ("icon_class", models.CharField(blank=True, help_text="Optional Font Awesome class.", max_length=100)), ("open_in_new_tab", models.BooleanField(default=False)), ("sort_order", models.PositiveIntegerField(default=0)), ("is_active", models.BooleanField(default=True)), ("section", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="links", to="website.footersection"))], options={"ordering": ("sort_order", "id")}),
        migrations.RunPython(seed_footer, migrations.RunPython.noop),
    ]
