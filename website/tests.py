from django.contrib import admin
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.test import TestCase
from django.urls import reverse
from tempfile import TemporaryDirectory
from bs4 import BeautifulSoup

from chhabi_api.models import MobileAttendanceEvidence
from employee.models import Employee

from .models import FooterLink, FooterSection, FooterSocialLink, WebsiteService, WebsiteSubmission


class WebsiteCmsTests(TestCase):
    def test_public_pages_render_and_structured_content_is_injected(self):
        WebsiteService.objects.create(name="Security Review", slug="security-review", short_description="Secure delivery", is_active=True)
        for url in ("/", "/about/", "/services/", "/pricing/", "/career/", "/contact/", "/terms-and-conditions/"):
            self.assertEqual(self.client.get(url).status_code, 200)
        self.assertContains(self.client.get("/services/"), "Security Review")

    def test_dynamic_section_replaces_static_section_before_footer(self):
        WebsitePage.objects.update_or_create(
            slug="services",
            defaults={
                "title": "Services",
                "is_published": True,
                "html_content": (
                    '<html><head><title>Services</title></head><body>'
                    '<section class="our-services-section">OLD STATIC SERVICE</section>'
                    '<!-- Footer-Section --><div class="footer-section">Footer</div>'
                    '</body></html>'
                ),
            },
        )
        WebsiteService.objects.create(
            name="Managed Service", slug="managed-service", is_active=True
        )
        content = self.client.get("/services/").content.decode()
        self.assertNotIn("OLD STATIC SERVICE", content)
        self.assertLess(content.index("DYNAMIC-CMS"), content.index("Footer-Section"))

    def test_contact_submission_is_saved(self):
        response = self.client.post(reverse("website-submit"), {"name": "Test User", "email": "test@example.com", "message": "Hello"})
        self.assertRedirects(response, reverse("website-thank-you"))
        self.assertTrue(WebsiteSubmission.objects.filter(email="test@example.com").exists())

    def test_website_models_are_protected_by_django_admin_auth(self):
        response = self.client.get("/website/manage/services/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)
        self.assertEqual(self.client.get("/website/manage/website/websiteservice/").status_code, 404)
        self.assertEqual(self.client.get("/admin/website/websiteservice/").status_code, 404)
        self.assertTrue(admin.site.is_registered(WebsiteService))


class AttendanceEvidenceManagerTests(TestCase):
    def setUp(self):
        self.media = TemporaryDirectory()
        self.settings_override = override_settings(MEDIA_ROOT=self.media.name)
        self.settings_override.enable()
        self.admin = User.objects.create_superuser("evidence-admin", "admin@example.com", "secret")
        Employee.objects.create(
            employee_user_id=self.admin,
            employee_first_name="Admin",
            email="admin@example.com",
            phone="8888888888",
        )
        self.employee = Employee.objects.create(
            employee_user_id=User.objects.create_user("field-user"),
            employee_first_name="Field",
            employee_last_name="Employee",
            email="field@example.com",
            phone="9999999999",
            badge_id="EMP-101",
        )
        self.evidence = MobileAttendanceEvidence.objects.create(
            employee=self.employee,
            action="clock-in",
            latitude="28.6139391",
            longitude="77.2090212",
            accuracy=8.5,
            biometric_verified=True,
            selfie=SimpleUploadedFile("selfie.gif", b"GIF89a\x01\x00\x01\x00\x00\x00\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;", content_type="image/gif"),
        )

    def tearDown(self):
        self.settings_override.disable()
        self.media.cleanup()

    def test_admin_sees_employee_selfie_and_exact_location(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("website-attendance-evidence"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Field Employee")
        self.assertContains(response, "28.6139391")
        self.assertContains(response, "77.2090212")
        self.assertContains(response, "Open exact point in Google Maps")
        selfie = self.client.get(reverse("website-attendance-selfie", args=(self.evidence.pk,)))
        self.assertEqual(selfie.status_code, 200)
        selfie.close()


from .models import WebsitePage, WebsiteSettings, WebsiteSubmission


class PublicWebsiteTests(TestCase):
    def setUp(self):
        WebsiteSettings.objects.update_or_create(pk=1, defaults={"company_name": "Test Company", "email": "hello@example.com"})
        WebsitePage.objects.update_or_create(slug="home", defaults={"title": "Home", "html_content": '<html><head><title>Old</title></head><body>Geeta ForgeTech<img src="assets/x.png"></body></html>'})
        WebsitePage.objects.update_or_create(slug="thank-you", defaults={"title": "Thanks", "html_content": "<html>Thanks</html>"})

    def test_root_renders_database_page_and_dynamic_company(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Company")
        self.assertContains(response, "/static/website/assets/x.png")

    def test_submission_is_saved_locally(self):
        response = self.client.post(reverse("website-submit"), {"name": "A", "email": "a@example.com", "message": "Hello"})
        self.assertRedirects(response, reverse("website-thank-you"))
        self.assertEqual(WebsiteSubmission.objects.count(), 1)
        self.assertEqual(WebsiteSubmission.objects.get().message, "Hello")

    def test_welcome_popup_consultation_is_saved_in_backend(self):
        response = self.client.post(reverse("website-submit"), {
            "submission_type": "consultation",
            "_subject": "Welcome Consultation Message from Website",
            "name": "Popup User",
            "email": "popup@example.com",
            "phone": "9876543210",
            "message": "I need a security consultation.",
        })
        self.assertRedirects(response, reverse("website-thank-you"))
        saved = WebsiteSubmission.objects.get(email="popup@example.com")
        self.assertEqual(saved.submission_type, WebsiteSubmission.CONSULTATION)
        self.assertEqual(saved.phone, "9876543210")
        self.assertEqual(saved.message, "I need a security consultation.")
        self.assertEqual(saved.extra_data["source"], "welcome_popup")

    def test_footer_is_rendered_from_admin_managed_records(self):
        page = WebsitePage.objects.get(slug="home")
        page.html_content = '<html><head><title>Home</title></head><body><div class="footer-section">OLD STATIC FOOTER</div></body></html>'
        page.save()
        FooterSection.objects.all().delete()
        FooterSocialLink.objects.all().delete()
        section = FooterSection.objects.create(title="Customer Resources", section_type="links")
        FooterLink.objects.create(section=section, label="Support Centre", url="/contact/")
        FooterSocialLink.objects.create(platform="GitHub", url="https://github.com/example", icon_class="fa-brands fa-github")
        site = WebsiteSettings.objects.get(pk=1)
        site.footer_text = "A fully managed footer description."
        site.save()

        response = self.client.get("/")
        self.assertContains(response, "Customer Resources")
        self.assertContains(response, "Support Centre")
        self.assertContains(response, "A fully managed footer description.")
        self.assertContains(response, "https://github.com/example")
        self.assertNotContains(response, "OLD STATIC FOOTER")

    def test_terms_link_is_only_in_footer_not_header(self):
        terms_html = '<html><head><title>Terms</title></head><body><ul class="navbar-nav"></ul><div class="footer-section">old</div></body></html>'
        WebsitePage.objects.update_or_create(slug="terms-and-conditions", defaults={"title": "Terms & Conditions", "html_content": terms_html, "is_published": True})
        page = WebsitePage.objects.get(slug="home")
        page.html_content = '<html><head><title>Home</title></head><body><ul class="navbar-nav"></ul><div class="footer-section">old</div></body></html>'
        page.save()
        legal = FooterSection.objects.create(title="Legal", section_type="links")
        FooterLink.objects.create(section=legal, label="Terms & Conditions", url="/terms-and-conditions/")

        home = self.client.get("/")
        soup = BeautifulSoup(home.content, "html.parser")
        self.assertIsNone(soup.select_one('.navbar-nav a[href="/terms-and-conditions/"]'))
        self.assertIsNotNone(soup.select_one('.dynamic-footer a[href="/terms-and-conditions/"]'))
        self.assertIsNotNone(soup.select_one("#uncropped-logo-styles"))
        self.assertContains(self.client.get("/terms-and-conditions/"), "Terms &amp; Conditions")
