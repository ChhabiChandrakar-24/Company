import re
from pathlib import Path
from urllib.parse import quote

from bs4 import BeautifulSoup

from django.conf import settings
from django.contrib import messages
from django.http import Http404, HttpResponse
from django.db.models import Q
from django.middleware.csrf import get_token
from django.shortcuts import redirect
from django.utils.html import escape

from .models import (
    FooterSection,
    FooterSocialLink,
    JobOpening,
    PricingPlan,
    TeamMember,
    WebsitePage,
    WebsiteService,
    WebsiteSettings,
    WebsiteSubmission,
    FAQ,
    PortfolioProject,
    Testimonial,
    ThemeSettings,
    WebsiteProduct,
    CarouselSlide,
)


PAGE_FILES = {
    "home": "index.html", "about": "about.html", "services": "services.html",
    "pricing": "pricing.html", "career": "career.html", "contact": "contact.html",
    "faq": "faq.html", "team": "our-team.html", "projects": "project.html",
    "terms-and-conditions": "terms-and-conditions.html",
    "thank-you": "thankyou.html",
}


def _site_settings():
    obj = WebsiteSettings.objects.first()
    return obj or WebsiteSettings()


def _page_html(slug):
    page = WebsitePage.objects.prefetch_related("sections__section_items").filter(slug=slug, status="published").first()
    if page:
        return page.html_content, page
    filename = PAGE_FILES.get(slug)
    if not filename:
        raise Http404
    path = Path(settings.BASE_DIR) / "web" / filename
    if not path.exists():
        raise Http404
    return path.read_text(encoding="utf-8", errors="replace"), None


def _render_public_html(request, html, page=None):
    site = _site_settings()
    routes = {
        "index.html": "/", "about.html": "/about/", "services.html": "/services/",
        "pricing.html": "/pricing/", "career.html": "/career/", "contact.html": "/contact/",
        "faq.html": "/faq/", "our-team.html": "/team/", "project.html": "/projects/",
        "terms-and-conditions.html": "/terms-and-conditions/",
        "thankyou.html": "/thank-you/",
    }
    for old, new in routes.items():
        html = re.sub(rf'(?i)(href|action)=["\']{re.escape(old)}["\']', rf'\1="{new}"', html)
    html = re.sub(r'(?i)(src|href)=["\']assets/', r'\1="/static/website/assets/', html)
    html = html.replace("../../cdnjs.cloudflare.com/", "https://cdnjs.cloudflare.com/")
    html = html.replace("../../unpkg.com/", "https://unpkg.com/")
    html = html.replace("../../code.jquery.com/", "https://code.jquery.com/")
    # The source theme references a font file that is not included in its assets.
    # Remove only that broken preload; the stylesheet already defines fallbacks.
    html = re.sub(
        r'<link[^>]+href=["\']fonts/poppins\.woff2["\'][^>]*>',
        "",
        html,
        flags=re.I,
    )
    html = html.replace("Geeta ForgeTech", site.company_name)
    html = html.replace("chcyberarmy@gmail.com", site.email)
    html = re.sub(r'\+91\s*8819981884', site.phone, html)
    html = re.sub(r'href=["\']tel:[^"\']+["\']', f'href="tel:{quote(site.phone)}"', html)
    html = re.sub(r'href=["\']mailto:[^"\']+["\']', f'href="mailto:{site.email}"', html)
    if site.logo:
        html = re.sub(r'/static/website/assets/images/logo/main_logo\.png', site.logo.url, html)
    if site.favicon:
        html = re.sub(r'/static/website/assets/images/logo/main_logo\.png', site.favicon.url, html, count=4)
    if page:
        html = re.sub(r'<title>.*?</title>', f'<title>{page.title}</title>', html, count=1, flags=re.I | re.S)
        description = page.meta_description or site.default_meta_description
        keywords = page.meta_keywords or site.default_meta_keywords
        if description:
            html = re.sub(r'<meta\s+name="description"[^>]*>', f'<meta name="description" content="{description}">', html, count=1, flags=re.I)
        if keywords:
            html = re.sub(r'<meta\s+name="keywords"[^>]*>', f'<meta name="keywords" content="{keywords}">', html, count=1, flags=re.I)
        html = _inject_structured_content(html, page)

    nav_links = ""
    for nav_page in WebsitePage.objects.filter(show_in_navigation=True, status="published").order_by("navigation_order"):
        active = ' active' if (page and nav_page.slug == page.slug) else ''
        nav_links += f'<li class="nav-item{active}"><a class="nav-link text-decoration-none navbar-text-color" href="{nav_page.get_absolute_url()}">{escape(nav_page.title)}</a></li>'
    if nav_links:
        html = re.sub(r'(<ul\b[^>]*class=["\'][^"\']*\bnavbar-nav\b[^"\']*["\'][^>]*>).*?(</ul>)', rf'\1{nav_links}\2', html, count=1, flags=re.I | re.S)

    canonical_url = escape(request.build_absolute_uri(request.path))

    robots_meta = '<meta name="robots" content="noindex, follow">' if request.path == "/thank-you/" else '<meta name="robots" content="index, follow">'
    seo_meta = f'<link rel="canonical" href="{canonical_url}">{robots_meta}'
    html = re.sub(r"</head>", seo_meta + "</head>", html, count=1, flags=re.I)
    html = re.sub(
        r"</head>",
        """<style id="uncropped-logo-styles">
        .navbar-brand img,.header-section img[class*="logo"],.dynamic-footer-brand img,.footer-logo{
          width:auto!important;height:auto!important;max-width:220px!important;max-height:90px!important;
          object-fit:contain!important;object-position:center!important;
        }
        </style></head>""",
        html,
        count=1,
        flags=re.I,
    )
    html = _inject_dynamic_footer(html, site)
    # Keep submissions inside Django and add CSRF protection to every public form.
    html = re.sub(r'action=["\']https://formsubmit\.co/[^"\']+["\']', 'action="/website/submit/"', html, flags=re.I)
    token = get_token(request)
    hidden = f'<input type="hidden" name="csrfmiddlewaretoken" value="{token}">'
    html = re.sub(r'(<form\b[^>]*>)', rf'\1{hidden}', html, flags=re.I)
    return html


def _footer_section_html(section, site):
    title = escape(section.title)
    content = f'<p class="dynamic-footer-copy">{escape(section.content)}</p>' if section.content else ""
    if section.section_type == FooterSection.CONTACT:
        details = []
        if site.phone:
            details.append(f'<li><i class="fa fa-phone"></i><a href="tel:{escape(quote(site.phone))}">{escape(site.phone)}</a></li>')
        if site.email:
            details.append(f'<li><i class="fa fa-envelope"></i><a href="mailto:{escape(site.email)}">{escape(site.email)}</a></li>')
        if site.address:
            details.append(f'<li><i class="fa-solid fa-location-dot"></i><span>{escape(site.address)}</span></li>')
        body = content + f'<ul class="dynamic-footer-list dynamic-footer-contact">{"".join(details)}</ul>'
    elif section.section_type == FooterSection.NEWSLETTER:
        body = content + '''<form method="post" action="/website/submit/" class="dynamic-footer-newsletter">
          <input type="hidden" name="_subject" value="Newsletter subscription">
          <input type="email" name="email" required placeholder="Email address" aria-label="Email address">
          <button type="submit">Subscribe</button></form>'''
    else:
        links = []
        for link in section.links.filter(is_active=True):
            target = ' target="_blank" rel="noopener noreferrer"' if link.open_in_new_tab else ""
            icon = f'<i class="{escape(link.icon_class)}"></i>' if link.icon_class else ""
            links.append(f'<li><a href="{escape(link.url)}"{target}>{icon}{escape(link.label)}</a></li>')
        body = content + (f'<ul class="dynamic-footer-list">{"".join(links)}</ul>' if links else "")
    return f'<div class="dynamic-footer-column"><h5>{title}</h5>{body}</div>'


def _inject_dynamic_footer(html, site):
    soup = BeautifulSoup(html, "html.parser")
    old_footer = soup.select_one(".footer-section")
    if old_footer is None:
        return html
    logo = site.logo.url if site.logo else "/static/website/assets/images/logo/main_logo.jpeg"
    social_links = "".join(
        f'<a href="{escape(item.url)}" target="_blank" rel="noopener noreferrer" aria-label="{escape(item.platform)}"><i class="{escape(item.icon_class)}"></i></a>'
        for item in FooterSocialLink.objects.filter(is_active=True)
    )
    columns = "".join(_footer_section_html(section, site) for section in FooterSection.objects.filter(is_active=True).prefetch_related("links"))
    copyright_text = f'© {escape(str(site.company_name))}. All Rights Reserved.'
    footer_html = f'''<footer class="footer-section dynamic-footer">
      <div class="container"><div class="dynamic-footer-grid">
        <div class="dynamic-footer-brand"><a href="/"><img src="{escape(logo)}" alt="{escape(site.company_name)}"></a>
          <p>{escape(site.footer_text or site.tagline)}</p><div class="dynamic-footer-social">{social_links}</div></div>
        {columns}
      </div></div><div class="footer-bar text-center"><p>{copyright_text}</p></div>
    </footer>'''
    footer_styles = '''<style id="dynamic-footer-styles">
      .dynamic-footer{background:#101a35;color:#cbd3e1;padding-top:64px}.dynamic-footer-grid{display:grid;grid-template-columns:minmax(240px,1.35fr) repeat(auto-fit,minmax(180px,1fr));gap:42px;padding-bottom:48px}
      .dynamic-footer-brand img{max-width:190px;max-height:74px;object-fit:contain;margin-bottom:20px}.dynamic-footer-brand p,.dynamic-footer-copy{line-height:1.7;color:#cbd3e1}.dynamic-footer-column h5{color:#fff;margin-bottom:20px;font-size:18px}
      .dynamic-footer-list{list-style:none;padding:0;margin:0}.dynamic-footer-list li{margin:0 0 12px;display:flex;gap:10px;align-items:flex-start}.dynamic-footer-list a,.dynamic-footer-list span{color:#cbd3e1;text-decoration:none}.dynamic-footer-list a:hover{color:#ff8a1f}.dynamic-footer-list i{min-width:18px;margin-right:8px;color:#ff8a1f}
      .dynamic-footer-social{display:flex;gap:10px;margin-top:20px}.dynamic-footer-social a{display:grid;place-items:center;width:38px;height:38px;border-radius:50%;background:#1c2949;color:#fff;text-decoration:none}.dynamic-footer-social a:hover{background:#ff8a1f}
      .dynamic-footer-newsletter{display:flex;gap:8px;flex-wrap:wrap}.dynamic-footer-newsletter input{min-width:0;flex:1;padding:12px;border:0;border-radius:7px}.dynamic-footer-newsletter button{border:0;border-radius:7px;background:#ff8a1f;color:#fff;padding:12px 16px;font-weight:600}.dynamic-footer .footer-bar{border-top:1px solid #263451;padding:20px}.dynamic-footer .footer-bar p{margin:0;color:#aeb8ca}
      @media(max-width:767px){.dynamic-footer-grid{grid-template-columns:1fr;gap:30px}.dynamic-footer{padding-top:45px}}
    </style>'''
    old_footer.replace_with(BeautifulSoup(footer_html, "html.parser"))
    if soup.head:
        soup.head.append(BeautifulSoup(footer_styles, "html.parser"))
    return str(soup)


def _website_card(title, description, image="", meta="", action_url="", action_text="", extra=""):
    image_html = f'<img src="{escape(image)}" alt="{escape(title)}" class="cms-card-image">' if image else ""
    meta_html = f'<p class="cms-card-meta">{escape(meta)}</p>' if meta else ""
    action_html = f'<a href="{escape(action_url)}" class="cms-action">{escape(action_text)} <i class="fas fa-arrow-right"></i></a>' if action_url and action_text else ""
    return f'<div class="col-lg-4 col-md-6 mb-4"><article class="cms-card">{image_html}<div class="cms-card-body">{meta_html}<h3>{escape(title)}</h3><p>{escape(description)}</p>{extra}{action_html}</div></article></div>'


def _cms_section(heading, cards, subheading=""):
    subtitle = f'<p class="cms-section-subtitle">{escape(subheading)}</p>' if subheading else ""
    return f'''<!-- DYNAMIC-CMS:{escape(heading)} -->
    <section class="cms-managed-section">
      <div class="container">
        <div class="cms-section-heading"><h2>{escape(heading)}</h2>{subtitle}</div>
        <div class="row">{"".join(cards)}</div>
      </div>
    </section>'''


def _replace_section_by_class(html, class_name, replacement):
    pattern = rf'<section\b[^>]*class=["\'][^"\']*\b{re.escape(class_name)}\b[^"\']*["\'][^>]*>.*?</section>'
    return re.sub(pattern, replacement, html, count=1, flags=re.I | re.S)


def _insert_before(html, marker, block):
    if marker in html:
        return html.replace(marker, block + "\n" + marker, 1)
    # Safe fallback: content stays above the visual footer, never after it.
    footer = re.search(r'<div\b[^>]*class=["\'][^"\']*\bfooter-section\b', html, re.I)
    return html[:footer.start()] + block + "\n" + html[footer.start():] if footer else html


CMS_STYLES = '''<style id="dynamic-cms-styles">
.cms-managed-section{padding:80px 0;background:#f7f9fc}.cms-managed-section:nth-of-type(even){background:#fff}
.cms-section-heading{text-align:center;max-width:760px;margin:0 auto 42px}.cms-section-heading h2{font-size:42px;font-weight:700;margin-bottom:12px;color:#111b35}
.cms-section-subtitle{color:#667085;font-size:17px}.cms-card{height:100%;background:#fff;border:1px solid #edf0f5;border-radius:18px;box-shadow:0 12px 35px rgba(18,38,63,.08);overflow:hidden;transition:.25s ease}
.cms-card:hover{transform:translateY(-7px);box-shadow:0 20px 45px rgba(18,38,63,.14)}.cms-card-image{width:100%;height:220px;object-fit:cover}.cms-card-body{padding:28px}
.cms-card-body h3{font-size:23px;margin-bottom:12px;color:#111b35}.cms-card-body p{color:#667085;line-height:1.7}.cms-card-meta{color:#f57c00!important;font-weight:700;text-transform:uppercase;font-size:13px;letter-spacing:.4px}
.cms-action{display:inline-flex;align-items:center;gap:8px;margin-top:10px;color:#fff!important;background:linear-gradient(135deg,#ff7a00,#ff9e2a);padding:11px 20px;border-radius:9px;text-decoration:none!important;font-weight:600}
.cms-feature-list{list-style:none;padding:0;margin:18px 0}.cms-feature-list li{padding:7px 0;color:#475467}.cms-feature-list li:before{content:'✓';color:#ff7a00;font-weight:800;margin-right:9px}
@media(max-width:767px){.cms-managed-section{padding:55px 0}.cms-section-heading h2{font-size:32px}}
.cms-theme-dark{background:#111b35;color:#fff}.cms-theme-dark .cms-section-heading h2,.cms-theme-dark .cms-card-body h3{color:#fff}.cms-theme-dark .cms-card{background:#192642;border-color:#263655}.cms-theme-dark .cms-card-body p{color:#cbd3e1}
</style>'''


def _home_section(section, dark=False):
    cards = []
    for item in section.items:
        if not isinstance(item, dict):
            continue
        cards.append(_website_card(str(item.get("title", "")), str(item.get("description", ""))))
    theme = " cms-theme-dark" if dark else ""
    return f'''<!-- DYNAMIC-CMS:{escape(section.section_type)} --><section class="cms-managed-section{theme}"><div class="container">
      <div class="cms-section-heading"><h6 class="autorix-text">{escape(section.heading)}</h6><h2>{escape(section.subheading or section.heading)}</h2><p class="cms-section-subtitle">{escape(section.content)}</p></div>
      <div class="row">{"".join(cards)}</div></div></section>'''


def _inject_home_sections(html, section_map):
    hero = section_map.get("hero")
    if hero:
        html = re.sub(r'(<div\b[^>]*class=["\'][^"\']*\bhome-banner-text\b[^"\']*["\'][^>]*>\s*)<h1>.*?</h1>', rf'\1<h1>{escape(hero.heading)}</h1>', html, count=1, flags=re.I | re.S)
        html = re.sub(r'<p\b[^>]*class=["\'][^"\']*\bbanner-paragraph\b[^"\']*["\'][^>]*>.*?</p>', f'<p class="banner-paragraph">{escape(hero.content)}</p>', html, count=1, flags=re.I | re.S)
        buttons = "".join(f'<a href="{escape(str(item.get("url", "#")))}" class="text-decoration-none">{escape(str(item.get("title", "Learn More")))}</a>' for item in hero.items if isinstance(item, dict))
        html = re.sub(r'(<div\b[^>]*class=["\'][^"\']*\bbanner-btn\b[^"\']*["\'][^>]*>).*?(</div>)', rf'\1{buttons}\2', html, count=1, flags=re.I | re.S)
    about = section_map.get("about")
    if about:
        html = _replace_section_by_class(html, "about-us-section", _home_section(about))
    who = section_map.get("who_we_are")
    what = section_map.get("what_we_do")
    if who or what:
        combined = ( _home_section(who, True) if who else "") + (_home_section(what) if what else "")
        html = _replace_section_by_class(html, "who-we-are-section", combined)
    testimonials = Testimonial.objects.filter(is_active=True)
    if testimonials.exists():
        cards = [_website_card(t.author, f'"{t.quote}"', t.image.url if t.image else "", t.designation) for t in testimonials]
        html = _replace_section_by_class(html, "carousel-section", _cms_section("Testimonials", cards, "What our clients say"))
    else:
        testimonials = section_map.get("testimonials")
        if testimonials:
            html = _replace_section_by_class(html, "carousel-section", _home_section(testimonials, True))
    started = section_map.get("get_started")
    if started:
        contact = re.search(r'<section\b[^>]*class=["\'][^"\']*\bcontact-us-form\b[^"\']*["\'][^>]*>.*?</section>', html, re.I | re.S)
        if contact:
            block = contact.group(0)
            block = re.sub(r'<h6\b[^>]*>.*?</h6>', f'<h6 class="autorix-text text-center">{escape(started.heading)}</h6>', block, count=1, flags=re.I | re.S)
            block = re.sub(r'<h2\b[^>]*>.*?</h2>', f'<h2 class="text-center">{escape(started.content)}</h2>', block, count=1, flags=re.I | re.S)
            html = html[:contact.start()] + block + html[contact.end():]
    return html


def _inject_structured_content(html, page):
    # Structured records replace the corresponding legacy static section. They
    # are never appended after the footer.
    html = re.sub(r'</head>', CMS_STYLES + '</head>', html, count=1, flags=re.I)
    cards = []
    section_map = {section.section_type: section for section in page.sections.filter(is_active=True)}
    if page.slug == "home":
        html = _inject_home_sections(html, section_map)
    if page.slug in {"home", "services"}:
        cards = [_website_card(item.name, item.short_description, item.image.url if item.image else "") for item in WebsiteService.objects.filter(is_active=True)]
        block = _cms_section("Our Services", cards, "Solutions managed directly from the admin panel")
        html = _replace_section_by_class(html, "our-services-section", block)
        if page.slug == "home":
            price_cards = []
            for plan in PricingPlan.objects.filter(is_active=True):
                features = '<ul class="cms-feature-list">' + "".join(f'<li>{escape(feature)}</li>' for feature in plan.feature_list) + '</ul>'
                price_cards.append(_website_card(plan.name, plan.description, meta=f"₹{plan.price}/{plan.billing_period}", action_url=plan.button_url, action_text=plan.button_text, extra=features))
            html = _replace_section_by_class(html, "pricing-plan-section", _cms_section("Our Solutions & Pricing", price_cards, "Choose the right solution for your business"))
            team_cards = [_website_card(member.name, member.bio, member.image.url if member.image else "", member.designation) for member in TeamMember.objects.filter(is_active=True)]
            html = _replace_section_by_class(html, "our-teams-section", _cms_section("Our Team", team_cards, "The people behind our secure solutions"))
    elif page.slug == "pricing":
        for plan in PricingPlan.objects.filter(is_active=True):
            features = '<ul class="cms-feature-list">' + "".join(f'<li>{escape(feature)}</li>' for feature in plan.feature_list) + '</ul>'
            cards.append(_website_card(plan.name, plan.description, meta=f"₹{plan.price}/{plan.billing_period}", action_url=plan.button_url, action_text=plan.button_text, extra=features))
        html = _replace_section_by_class(html, "pricing-plan-section", _cms_section("Pricing Plans", cards, "Flexible plans for every stage of your business"))
    elif page.slug == "projects":
        for proj in PortfolioProject.objects.filter(is_active=True):
            cards.append(_website_card(proj.title, proj.short_description, proj.image.url if proj.image else ""))
        html = _replace_section_by_class(html, "our-services-section", _cms_section("Our Projects", cards, "Creative, Safe & Scalable Projects"))
    elif page.slug == "career":
        for job in JobOpening.objects.filter(is_active=True):
            apply_url = job.application_url or (f"mailto:{job.application_email}" if job.application_email else "/contact/")
            cards.append(_website_card(job.title, job.description, meta=" · ".join(filter(None, [job.location, job.job_type, job.experience])), action_url=apply_url, action_text="Apply Now"))
        html = _insert_before(html, '<section class="contact-us-form career-form-section">', _cms_section("Current Openings", cards, "Find the role where you can do your best work"))
        options = '<option value="">Select Position</option>' + "".join(f'<option value="{escape(job.title)}">{escape(job.title)}</option>' for job in JobOpening.objects.filter(is_active=True))
        html = re.sub(r'(<select\b[^>]*(?:name=["\'](?:position|job_position)["\']|id=["\'][^"\']*position[^"\']*["\'])[^>]*>).*?(</select>)', rf'\1{options}\2', html, count=1, flags=re.I | re.S)
    elif page.slug == "faq":
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
        html = re.sub(r'(<div\b[^>]*id=["\']accordion1["\'][^>]*>).*?(</div>\s*</div>\s*</div>)', rf'\1{"".join(faq_html)}\2', html, count=1, flags=re.I | re.S)
    elif page.slug in {"about", "team"}:
        cards = [_website_card(member.name, member.bio, member.image.url if member.image else "", member.designation) for member in TeamMember.objects.filter(is_active=True)]
        html = _replace_section_by_class(html, "our-teams-section", _cms_section("Our Team", cards, "Meet the people behind our work"))

    content_blocks = []
    handled_home_types = {"hero", "about", "who_we_are", "what_we_do", "testimonials", "get_started"}
    for section in page.sections.filter(is_active=True):
        if page.slug == "home" and section.section_type in handled_home_types:
            continue
        item_cards = "".join(_website_card(str(item.get("title", "")), str(item.get("description", item.get("value", "")))) for item in section.items if isinstance(item, dict))
        image_html = f'<img src="{escape(section.image.url)}" alt="{escape(section.heading)}" style="max-width:100%;border-radius:14px">' if section.image else ""
        content = f'<div class="cms-card-body"><p>{escape(section.content)}</p>{image_html}</div>' if section.content or image_html else ""
        content_blocks.append(f'<section class="cms-managed-section"><div class="container"><div class="cms-section-heading"><h2>{escape(section.heading)}</h2><p class="cms-section-subtitle">{escape(section.subheading)}</p></div>{content}<div class="row">{item_cards}</div></div></section>')
    if content_blocks:
        block = "".join(content_blocks)
        if page.slug == "about":
            html = re.sub(r'<section\b[^>]*class=["\'][^"\']*\bmission-vision-section\b[^"\']*["\'][^>]*>.*?</section>\s*(?:<!--Whychoose-Us-SECTION -->\s*)?<section\b[^>]*class=["\'][^"\']*\bwhychooseus-section\b[^"\']*["\'][^>]*>.*?</section>', block, html, count=1, flags=re.I | re.S)
        else:
            html = _insert_before(html, '<!-- Footer-Section -->', block)
    return html


from django.shortcuts import get_object_or_404, render
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import cache_page


def public_page(request, slug="home"):
    """Render a CMS page or fallback to static HTML with injected dynamic content.
    If a page with the given slug doesn't exist, raise 404.
    """
    page = WebsitePage.objects.filter(slug=slug, status="published").first()
    
    if page and page.is_dynamic_render:
        # Load necessary global contexts
        site_settings = _site_settings()
        
        from website.models import NavigationMenu
        main_menu = NavigationMenu.objects.filter(slug="main", is_active=True).first()
        footer_menu = NavigationMenu.objects.filter(slug="footer", is_active=True).first()
        
        main_menu_items = main_menu.items.filter(parent__isnull=True, is_active=True).prefetch_related("children").order_by("sort_order") if main_menu else []
        footer_menu_items = footer_menu.items.filter(parent__isnull=True, is_active=True).order_by("sort_order") if footer_menu else []
        
        context = {
            "page": page,
            "site_settings": site_settings,
            "main_menu_items": main_menu_items,
            "footer_menu_items": footer_menu_items,
            "footer_sections": FooterSection.objects.filter(is_active=True).prefetch_related("links"),
            "social_links": FooterSocialLink.objects.filter(is_active=True),
            "theme_settings": ThemeSettings.objects.filter(is_active=True).first(),
            "services": WebsiteService.objects.filter(is_active=True),
            "pricing_plans": PricingPlan.objects.filter(is_active=True),
            "job_openings": JobOpening.objects.filter(is_active=True),
            "portfolio_projects": PortfolioProject.objects.filter(is_active=True),
            "products": WebsiteProduct.objects.filter(is_active=True),
            "carousel_slides": CarouselSlide.objects.filter(is_active=True).order_by("sort_order", "id"),
            "team_members": TeamMember.objects.filter(is_active=True),
            "testimonials": Testimonial.objects.filter(is_active=True),
            "faqs": FAQ.objects.filter(is_active=True),
            "seo_title": page.seo_title or page.title,
        }
        return render(request, "website/dynamic_page.html", context)

    html, page = _page_html(slug)
    return HttpResponse(_render_public_html(request, html, page))


def public_search(request):
    """Search only published public CMS content; never internal business data."""
    query = request.GET.get("q", "").strip()[:120]
    results = []
    if len(query) >= 2:
        pages = WebsitePage.objects.filter(status="published").filter(
            Q(title__icontains=query) | Q(meta_description__icontains=query)
            | Q(meta_keywords__icontains=query) | Q(focus_keyword__icontains=query)
            | Q(additional_keywords__icontains=query)
        )[:10]
        services = WebsiteService.objects.filter(is_active=True).filter(
            Q(name__icontains=query) | Q(short_description__icontains=query) | Q(keywords__icontains=query)
        )[:10]
        products = WebsiteProduct.objects.filter(is_active=True).filter(
            Q(name__icontains=query) | Q(short_description__icontains=query) | Q(keywords__icontains=query)
        )[:10]
        projects = PortfolioProject.objects.filter(is_active=True).filter(
            Q(title__icontains=query) | Q(short_description__icontains=query) | Q(keywords__icontains=query)
        )[:10]
        results.extend({"title": x.title, "description": x.meta_description, "url": x.get_absolute_url(), "type": "Page"} for x in pages)
        results.extend({"title": x.name, "description": x.short_description, "url": "/services/", "type": "Service"} for x in services)
        results.extend({"title": x.name, "description": x.short_description, "url": x.button_url, "type": x.get_item_type_display()} for x in products)
        results.extend({"title": x.title, "description": x.short_description, "url": "/projects/", "type": "Project"} for x in projects)
    from website.models import NavigationMenu
    main_menu = NavigationMenu.objects.filter(slug="main", is_active=True).first()
    footer_menu = NavigationMenu.objects.filter(slug="footer", is_active=True).first()
    return render(request, "website/search.html", {
        "query": query, "results": results, "site_settings": _site_settings(), "seo_title": "Search",
        "page": {"title": "Search", "meta_description": "Search public website content.", "meta_keywords": "", "focus_keyword": "", "additional_keywords": "", "canonical_url": "", "social_title": "Search", "social_description": "Search public website content."},
        "main_menu_items": main_menu.items.filter(parent__isnull=True, is_active=True).prefetch_related("children") if main_menu else [],
        "footer_menu_items": footer_menu.items.filter(parent__isnull=True, is_active=True) if footer_menu else [],
        "footer_sections": FooterSection.objects.filter(is_active=True).prefetch_related("links"),
        "social_links": FooterSocialLink.objects.filter(is_active=True),
        "theme_settings": ThemeSettings.objects.filter(is_active=True).first(),
    })

@staff_member_required
def preview_page(request, pk):
    """Staff‑only preview of a draft or published page."""
    page = get_object_or_404(WebsitePage, pk=pk)
    html, _ = _page_html(page.slug)
    return HttpResponse(_render_public_html(request, html, page))

def robots_txt(request):
    """Advertise the canonical sitemap while keeping private Django routes out."""
    sitemap_url = request.build_absolute_uri("/sitemap.xml")
    content = "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            "Disallow: /accounts/",
            "Disallow: /employee/",
            "Disallow: /report/",
            "Disallow: /website/manage/",
            "Disallow: /website/submit/",
            f"Sitemap: {sitemap_url}",
            "",
        ]
    )
    return HttpResponse(content, content_type="text/plain; charset=utf-8")


def submit(request):
    if request.method != "POST":
        return redirect("website-home")
    subject = request.POST.get("_subject", "").lower()
    referer = request.META.get("HTTP_REFERER", "").lower()
    kind = WebsiteSubmission.CONTACT
    requested_kind = request.POST.get("submission_type", "").lower()
    if requested_kind == WebsiteSubmission.CONSULTATION or "consultation" in subject:
        kind = WebsiteSubmission.CONSULTATION
    elif "newsletter" in subject or (not request.POST.get("message") and request.POST.get("email")):
        kind = WebsiteSubmission.NEWSLETTER
    elif "career" in referer:
        kind = WebsiteSubmission.CAREER
    ignored = {"csrfmiddlewaretoken", "submission_type", "name", "email", "phone", "message", "_next", "_captcha", "_subject", "_template"}
    extra = {key: value for key, value in request.POST.items() if key not in ignored}
    WebsiteSubmission.objects.create(
        submission_type=kind, name=request.POST.get("name", "")[:150],
        email=request.POST.get("email", "")[:254], phone=request.POST.get("phone", "")[:50],
        message=request.POST.get("message", ""),
        extra_data={"source": "welcome_popup" if kind == WebsiteSubmission.CONSULTATION else "website", **extra},
    )
    messages.success(request, "Thank you. Your details have been submitted successfully.")
    return redirect("website-thank-you")
