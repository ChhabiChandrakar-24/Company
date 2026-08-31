from django.contrib.staticfiles import finders
from django.core.files.storage import FileSystemStorage
from django.test import SimpleTestCase, override_settings
from django.templatetags.static import static


class AuthenticatedStaticAssetTests(SimpleTestCase):
    """Prevent the authenticated layout's compiled bundles disappearing again."""

    dashboard_assets = (
        "build/css/driver.min.css",
        "build/css/style.min.css",
        "build/css/sweetalert2.min.css",
        "build/css/summernote-lite.min.css",
        "build/css/orgChart.css",
        "build/css/pivottable.min.css",
        "build/js/web.frontend.min.js",
    )

    def test_dashboard_bundles_are_discoverable(self):
        for asset in self.dashboard_assets:
            with self.subTest(asset=asset):
                self.assertIsNotNone(finders.find(asset))

    def test_static_urls_are_root_relative_without_double_slashes(self):
        for asset in self.dashboard_assets:
            with self.subTest(asset=asset):
                url = static(asset)
                self.assertTrue(url.startswith("/static/"), url)
                self.assertNotIn("//static/", url)


class CompanyLogoTests(SimpleTestCase):
    @override_settings(STATIC_URL="/static/")
    def test_missing_logo_record_uses_bundled_default(self):
        from base.company_logo import (
            company_logo_url,
            open_company_logo,
            open_default_company_logo,
        )
        from base.models import Company

        company = Company(company="Missing logo")
        company.icon.name = "company_logo/missing.jpeg"
        company.icon.storage = FileSystemStorage(location=self._testMethodName)

        self.assertEqual(
            company_logo_url(company), "/static/chhabi/geeta-forgetech-logo.jpeg"
        )
        self.assertIsNone(open_company_logo(company))
        with open_default_company_logo() as default_logo:
            self.assertGreater(len(default_logo.read()), 0)
