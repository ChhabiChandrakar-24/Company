import re
from bs4 import BeautifulSoup
from django.conf import settings
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chhabi.settings")
django.setup()

html = open("web/index.html", encoding="utf-8").read()

# Make links dynamic
html = re.sub(r'(href|src)=["\']assets/', r'\1="{% static \'website/assets/', html)
html = html.replace('.css"', '.css\' %}"').replace('.js"', '.js\' %}"').replace('.png"', '.png\' %}"').replace('.jpg"', '.jpg\' %}"').replace('.jpeg"', '.jpeg\' %}"').replace('.woff2"', '.woff2\' %}"')
html = html.replace("../../cdnjs.cloudflare.com/", "https://cdnjs.cloudflare.com/")
html = html.replace("../../unpkg.com/", "https://unpkg.com/")
html = html.replace("../../code.jquery.com/", "https://code.jquery.com/")

html = "{% load static %}\n" + html

soup = BeautifulSoup(html, "html.parser")

if soup.title:
    soup.title.string = "{{ seo_title|default:page.title|default:site_settings.company_name }}"

meta_desc = soup.find("meta", {"name": "description"})
if meta_desc:
    meta_desc["content"] = "{{ page.meta_description|default:site_settings.default_meta_description }}"

meta_kw = soup.find("meta", {"name": "keywords"})
if meta_kw:
    meta_kw["content"] = "{{ page.meta_keywords|default:site_settings.default_meta_keywords }}"

html_str = str(soup)

# We want to replace everything inside the body between the nav/header and the footer.
header_match = re.search(r'</header>|<nav\b[^>]*>.*?</nav>', html_str, re.I | re.S)
header_end = header_match.end() if header_match else html_str.find("<body>") + 6

footer_match = re.search(r'<div\b[^>]*class=["\'][^"\']*\bfooter-section\b', html_str, re.I)
footer_start = footer_match.start() if footer_match else html_str.find("</body>")

dynamic_base = html_str[:header_end] + "\n\n<main>\n{% block content %}\n{% endblock %}\n</main>\n\n" + html_str[footer_start:]

# Fix CSRF
dynamic_base = re.sub(r'(<form\b[^>]*>)', r'\1\n{% csrf_token %}', dynamic_base, flags=re.I)
# Replace action with Django url tag if it's hitting a python view, else leave it.

os.makedirs("website/templates/website", exist_ok=True)
with open("website/templates/website/dynamic_base.html", "w", encoding="utf-8") as f:
    f.write(dynamic_base)
print("dynamic_base.html generated successfully!")
