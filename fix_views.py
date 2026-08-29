import re

with open("website/views.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add new models to imports
content = content.replace("WebsiteSettings,\n    WebsiteSubmission,", "WebsiteSettings,\n    WebsiteSubmission,\n    FAQ,\n    PortfolioProject,\n    Testimonial,")

# Replace navigation bar
nav_replacement_code = """
    nav_links = ""
    for nav_page in WebsitePage.objects.filter(show_in_navigation=True, status="published").order_by("navigation_order"):
        active = ' active' if (page and nav_page.slug == page.slug) else ''
        nav_links += f'<li class="nav-item{active}"><a class="nav-link text-decoration-none navbar-text-color" href="{nav_page.get_absolute_url()}">{escape(nav_page.title)}</a></li>'
    if nav_links:
        html = re.sub(r'(<ul\\b[^>]*class=["\\'][^"\\']*\\bnavbar-nav\\b[^"\\']*["\\'][^>]*>).*?(</ul>)', rf'\\1{nav_links}\\2', html, count=1, flags=re.I | re.S)

    canonical_url = escape(request.build_absolute_uri(request.path))
"""
content = content.replace("    canonical_url = escape(request.build_absolute_uri(request.path))", nav_replacement_code, 1)

# Add Home Testimonials
home_testimonials_code = """    testimonials = section_map.get("testimonials")
    if testimonials:
        html = _replace_section_by_class(html, "carousel-section", _home_section(testimonials, True))"""
home_testimonials_replacement = """    testimonials = Testimonial.objects.filter(is_active=True)
    if testimonials.exists():
        cards = [_website_card(t.author, f'"{t.quote}"', t.image.url if t.image else "", t.designation) for t in testimonials]
        html = _replace_section_by_class(html, "carousel-section", _cms_section("Testimonials", cards, "What our clients say"))
    else:
        testimonials = section_map.get("testimonials")
        if testimonials:
            html = _replace_section_by_class(html, "carousel-section", _home_section(testimonials, True))"""
content = content.replace(home_testimonials_code, home_testimonials_replacement, 1)

# Add Projects
projects_replacement_code = """    elif page.slug == "career":"""
projects_replacement = """    elif page.slug == "projects":
        for proj in PortfolioProject.objects.filter(is_active=True):
            cards.append(_website_card(proj.title, proj.short_description, proj.image.url if proj.image else ""))
        html = _replace_section_by_class(html, "our-services-section", _cms_section("Our Projects", cards, "Creative, Safe & Scalable Projects"))
    elif page.slug == "career":"""
content = content.replace(projects_replacement_code, projects_replacement, 1)

# Add FAQ
faq_replacement_code = """    elif page.slug in {"about", "team"}:"""
faq_replacement = """    elif page.slug == "faq":
        faq_html = []
        for index, faq in enumerate(FAQ.objects.filter(is_active=True), start=1):
            faq_html.append(f'''
<div class="accordion-card">
 <div class="card-header" id="heading{index}">
  <button aria-controls="collapse{index}" aria-expanded="{"true" if index==1 else "false"}" class="btn btn-link {'collapsed' if index!=1 else ''}" data-target="#collapse{index}" data-toggle="collapse">
   <span>{escape(faq.question)}</span>
  </button>
 </div>
 <div aria-labelledby="heading{index}" class="collapse {'show' if index==1 else ''}" data-parent="#accordion1" id="collapse{index}">
  <div class="card-body">
   <p>{escape(faq.answer)}</p>
  </div>
 </div>
</div>
            ''')
        html = re.sub(r'(<div\\b[^>]*id=["\']accordion1["\'][^>]*>).*?(</div>\\s*</div>\\s*</div>)', rf'\\1{"".join(faq_html)}\\2', html, count=1, flags=re.I | re.S)
    elif page.slug in {"about", "team"}:"""
content = content.replace(faq_replacement_code, faq_replacement, 1)

with open("website/views.py", "w", encoding="utf-8") as f:
    f.write(content)
