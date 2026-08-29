from django.test import TestCase
from ai_search.services.crawler import is_safe_url
from ai_search.services.seo_engine import analyze_seo

class CrawlerSecurityTests(TestCase):
    def test_localhost_blocked(self):
        self.assertFalse(is_safe_url('http://127.0.0.1:8000/'))
        self.assertFalse(is_safe_url('http://localhost:8080/'))
        
    def test_private_ip_blocked(self):
        self.assertFalse(is_safe_url('http://192.168.1.5/'))
        self.assertFalse(is_safe_url('http://10.0.0.1/'))
        
    def test_valid_public_url_allowed(self):
        self.assertTrue(is_safe_url('https://google.com'))
        
    def test_invalid_scheme_blocked(self):
        self.assertFalse(is_safe_url('ftp://server.com/'))

class SEOEngineTests(TestCase):
    def test_missing_title(self):
        data = {'title': None}
        score, issues = analyze_seo(data, [])
        self.assertLess(score, 100)
        self.assertTrue(any(i['title'] == 'Missing Title Tag' for i in issues))
        
    def test_perfect_basic_seo(self):
        data = {
            'title': 'Perfect Page',
            'meta_description': 'A very good description',
            'h1_headings': ['Main Heading'],
            'images_count': 1,
            'images_with_alt': 1,
            'canonical_url': 'https://example.com',
            'internal_links_count': 5,
            'has_structured_data': True
        }
        score, issues = analyze_seo(data, ['Perfect Page'])
        self.assertEqual(score, 100)
        self.assertEqual(len(issues), 0)
