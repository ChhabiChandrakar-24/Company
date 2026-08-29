with open('website/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'additional_keywords' not in content:
    content = content.replace('focus_keyword = models.CharField(max_length=180, blank=True)', 
                              'focus_keyword = models.CharField(max_length=180, blank=True)\n    additional_keywords = models.TextField(blank=True, default="")')

if 'social_title' not in content:
    content = content.replace('canonical_url = models.URLField(blank=True)', 
                              'canonical_url = models.URLField(blank=True)\n    social_title = models.CharField(max_length=200, blank=True, default="")\n    social_description = models.TextField(blank=True, default="")\n    social_image = models.ImageField(upload_to="website/social/", blank=True)')

with open('website/models.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Patched fields!")
