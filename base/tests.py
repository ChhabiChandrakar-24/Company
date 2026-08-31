from django.contrib.staticfiles import finders
from django.test import SimpleTestCase
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
