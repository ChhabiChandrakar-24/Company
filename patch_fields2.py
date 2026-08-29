with open('website/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

replacement = '''    seo_title = models.CharField(max_length=200, blank=True, help_text="Override the page title for SEO purposes")
    focus_keyword = models.CharField(max_length=180, blank=True)
    additional_keywords = models.TextField(blank=True, default="", help_text="Comma-separated supporting keywords.")
    canonical_url = models.URLField(blank=True, help_text="Optional canonical override.")
    social_title = models.CharField(max_length=200, blank=True, default="")
    social_description = models.TextField(blank=True, default="")
    social_image = models.ImageField(upload_to="website/social/", blank=True)'''

if 'focus_keyword' not in content:
    content = content.replace('    seo_title = models.CharField(max_length=200, blank=True, help_text="Override the page title for SEO purposes")', replacement)

# We also need to fix PortfolioProject to have keywords
replacement2 = '''    image = models.ImageField(upload_to="website/projects/", blank=True)
    keywords = models.CharField(max_length=500, blank=True, default="")'''

if 'keywords = models.CharField' not in content:
    content = content.replace('    image = models.ImageField(upload_to="website/projects/", blank=True)', replacement2)

with open('website/models.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Patched missing fields in models.py!")
