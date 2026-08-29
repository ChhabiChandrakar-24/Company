"""Premium public-website content seed (design-system demo data).

Idempotent: safe to run once on a fresh database and on databases that
already carry the earlier seed migrations. It never deletes existing
content that was clearly added by an admin afterwards (menu items,
carousel slides, products, projects, testimonials, FAQs are only created
when the relevant collection is empty; plans/team/footer are updated in
place by stable keys).
"""

from django.db import migrations

HOME_SECTIONS = {
    10: ("carousel", "Secure Software, Websites & IT Solutions You Can Trust", "Enterprise-grade engineering for growing businesses"),
    20: ("stats", "Trusted by Businesses Across India", "Results that speak for themselves"),
    30: ("services", "What We Do", "Full-cycle software & IT services under one roof"),
    40: ("products", "Products & Solutions", "Ready-made platforms we build, host and support"),
    50: ("projects", "Featured Work", "A snapshot of what we have delivered"),
    60: ("features", "Why Choose Us", "The edge every engagement gets with GFT"),
    70: ("tech", "Technologies We Work With", "A modern, battle-tested stack"),
    80: ("testimonials", "Clients Trust Us for a Reason", "Don't take our word for it"),
    90: ("faq", "Frequently Asked Questions", "Everything you need to know before you start"),
    100: ("cta", "Ready to Build Something Great?", "Book a free consultation — we respond within 24 hours."),
    110: ("contact", "Let's Start a Conversation", "Tell us about your project and we'll take it from there"),
}

STATS_ITEMS = [
    ("2K+", "Projects Delivered", "Web, mobile, cloud and security engagements"),
    ("17M+", "Users Served", "People on platforms we have built"),
    ("18K+", "Threats Blocked", "Cyber attacks stopped every single month"),
    ("99.9%", "Uptime SLA", "Monitored 24/7 by our own SOC"),
]

WHY_US_EXTRA = [
    ("fa-certificate", "Certified Security Experts", "CEH, OSCP and ISO-aligned practitioners on every team."),
    ("fa-indian-rupee-sign", "Transparent Pricing", "Fixed quotes, milestone billing, zero surprises."),
    ("fa-headset", "24/7 Support", "Real engineers on call — not ticket queues."),
]

TECH_ITEMS = [
    ("fa-python", "Python / Django"),
    ("fa-react", "React / Next.js"),
    ("fa-mobile-screen-button", "Flutter / React Native"),
    ("fa-cloud", "AWS / Azure / GCP"),
    ("fa-dharmachakra", "Kubernetes / Docker"),
    ("fa-database", "MySQL / PostgreSQL"),
    ("fa-robot", "Machine Learning / AI"),
    ("fa-shield-halved", "Cybersecurity"),
]

FAQ_ITEMS = [
    ("How long does a typical project take?", "A marketing website usually ships in 2–4 weeks, a custom web application in 6–12 weeks, and enterprise platforms in 3–6 months. You get a fixed milestone plan before we start."),
    ("Do you provide support after launch?", "Yes. Every engagement includes a support window, and we offer 24/7 managed support plans with guaranteed response times."),
    ("Can you take over an existing project or codebase?", "Absolutely. We do code audits, tech-debt cleanup and full project takeovers — including for platforms built by other vendors."),
    ("How do you keep our data and systems secure?", "Security is baked into our process: secure SDLC, regular penetration testing, 24/7 SOC monitoring and ISO-aligned policies."),
]

PRODUCTS = [
    ("Horilla HRMS", "product", "fa-cubes-stacked", "Open-source HRMS — recruitment, onboarding, payroll, attendance, leave and performance in one clean platform.", "HR, Payroll, Attendance, Leave"),
    ("GFT ERP Suite", "solution", "fa-cubes", "End-to-end ERP for manufacturing and services: inventory, finance, procurement and analytics on a single source of truth.", "ERP, Inventory, Finance, Analytics"),
    ("CyberShield SOC", "solution", "fa-shield-halved", "Managed 24/7 security operations: monitoring, threat hunting, incident response and compliance reporting.", "SOC, Monitoring, Threat Hunting, Compliance"),
]

PROJECTS = [
    ("Horilla HRMS Platform", "A full-featured, open-source HRMS used by thousands of organisations — designed for scale, security and ease of use."),
    ("Smart Campus ERP", "Unified ERP for education: admissions, fees, exams, transport and parent communication for 12+ institutions."),
    ("Banking Analytics Portal", "Real-time MIS and risk analytics dashboard for a mid-size NBFC — 17M+ transactions processed monthly."),
]

TESTIMONIALS = [
    ("Rohit Sharma", "CTO, TechNova Labs", "GFT delivered our platform two weeks early and the code quality was outstanding. Their security review caught issues our previous vendor missed entirely."),
    ("Priya Verma", "Founder, EduNest", "From wireframes to launch, the team treated our product like their own. Uptime has been rock solid since day one."),
    ("Arjun Mehta", "COO, FinEdge Capital", "Their 24/7 SOC blocked a coordinated phishing campaign within minutes. That level of vigilance is exactly why we keep them on retainer."),
]

TEAM_EXTRA = [
    ("Ananya Singh", "Co-founder & CTO", "Full-stack architect with 12+ years across fintech and SaaS platforms."),
    ("Vikram Patel", "Lead Cloud Architect", "AWS & Kubernetes specialist who has migrated 40+ workloads to the cloud."),
    ("Sneha Reddy", "Head of Cyber Security", "CEH & OSCP certified, leads our 24/7 SOC and penetration testing practice."),
]

PRICING = {
    "Starter": {
        "price": "24999", "billing_period": "project",
        "description": "For small businesses that need a modern web presence fast.",
        "features": "Up to 6 page CMS website\nMobile responsive design\nBasic on-page SEO\nContact & enquiry forms\n1 month support",
        "button_text": "Get Started", "button_url": "/contact/",
    },
    "Business": {
        "price": "59999", "billing_period": "project",
        "description": "Custom web applications and portals for growing teams.",
        "features": "Everything in Starter\nCustom web application\nAdmin dashboard\nAPI integrations\nSecurity hardening & SSL\n3 months support",
        "button_text": "Get Started", "button_url": "/contact/",
    },
    "Enterprise": {
        "price": "149999", "billing_period": "project",
        "description": "ERP, HRMS and large-scale platforms with dedicated engineering.",
        "features": "Everything in Business\nDedicated engineering team\nLoad & performance testing\n24/7 SOC monitoring\nSLA-backed support\nQuarterly pen tests",
        "button_text": "Talk to Sales", "button_url": "/contact/",
    },
}

JOBS_EXTRA = [
    ("DevOps Engineer", "India / Remote", "Full Time", "2-4 years", "AWS, Kubernetes, CI/CD pipelines and infrastructure as code. You will own our deployment platform end-to-end."),
    ("UI/UX Designer", "Noida, India", "Full Time", "2-5 years", "Product designer who sweats the details — Figma mastery, design systems and accessible, premium interfaces."),
]


def _section(apps, page, sort_order, section_type, heading, subheading="", content=""):
    Section = apps.get_model("website", "WebsiteSection")
    section, _ = Section.objects.get_or_create(page=page, sort_order=sort_order)
    section.section_type = section_type
    section.heading = heading
    section.subheading = subheading
    section.content = content
    section.is_active = True
    section.save()
    return section


def _items(apps, section, rows):
    Item = apps.get_model("website", "WebsiteSectionItem")
    section.section_items.all().delete()
    for idx, data in enumerate(rows, start=1):
        Item.objects.create(section=section, sort_order=idx * 10, is_active=True, **data)


def _menu(apps, slug, name, parents):
    Menu = apps.get_model("website", "NavigationMenu")
    Item = apps.get_model("website", "NavigationItem")
    menu, _ = Menu.objects.get_or_create(slug=slug, defaults={"name": name})
    menu.name = name
    menu.is_active = True
    menu.save()
    if menu.items.exists():
        return menu  # preserve admin-managed items
    for sort, label, url, children in parents:
        parent = Item.objects.create(menu=menu, label=label, url=url, sort_order=sort, is_active=True)
        for c_sort, c_label, c_url in children:
            Item.objects.create(menu=menu, label=c_label, url=c_url, parent=parent, sort_order=c_sort, is_active=True)
    return menu


def seed(apps, schema_editor):
    Settings = apps.get_model("website", "WebsiteSettings")
    Page = apps.get_model("website", "WebsitePage")
    Service = apps.get_model("website", "WebsiteService")
    Product = apps.get_model("website", "WebsiteProduct")
    Project = apps.get_model("website", "PortfolioProject")
    Testimonial = apps.get_model("website", "Testimonial")
    FAQ = apps.get_model("website", "FAQ")
    Team = apps.get_model("website", "TeamMember")
    Price = apps.get_model("website", "PricingPlan")
    Job = apps.get_model("website", "JobOpening")
    Slide = apps.get_model("website", "CarouselSlide")
    Theme = apps.get_model("website", "ThemeSettings")
    MapCfg = apps.get_model("website", "ContactMapConfig")
    Footer = apps.get_model("website", "FooterSection")
    FooterLink = apps.get_model("website", "FooterLink")

    # ---- 1. Company settings (only if none exists) ----
    if not Settings.objects.exists():
        Settings.objects.create(
            company_name="Geeta ForgeTech",
            tagline="Secure Software, Websites & IT Solutions",
            phone="+91 8819981884",
            email="chcyberarmy@gmail.com",
            address="Sector 62, Noida,\nUttar Pradesh 201301, India",
            footer_text="Building secure, modern software that powers business growth.",
            office_hours="Mon – Sat, 9:30 AM – 7:00 PM IST",
            map_embed_url="https://www.google.com/maps?q=Sector%2062%2C%20Noida%2C%20Uttar%20Pradesh%20201301&output=embed",
            map_directions_url="https://www.google.com/maps/dir/?api=1&destination=Sector+62,+Noida,+Uttar+Pradesh+201301",
            header_cta_text="Get a Free Quote",
            header_cta_url="/contact/",
            default_meta_description="Geeta ForgeTech delivers secure software, websites, mobile apps, cloud and 24/7 cyber security solutions for growing businesses.",
            default_meta_keywords="software company, web development, mobile apps, cloud, devops, cyber security, ERP, HRMS, Noida",
        )

    # ---- 2. Home page sections (premium flow) ----
    home = Page.objects.get(slug="home")
    for sort_order, (section_type, heading, subheading) in HOME_SECTIONS.items():
        section = _section(apps, home, sort_order, section_type, heading, subheading)
        if section_type == "stats":
            _items(apps, section, [{"value": v, "title": t, "description": d} for v, t, d in STATS_ITEMS])
        elif section_type == "tech":
            _items(apps, section, [{"icon": i, "title": t} for i, t in TECH_ITEMS])
        elif section_type == "features":
            # Keep any existing items, then append the “Why Choose Us” extras
            existing = list(section.section_items.all())
            kept = [{"icon": it.icon, "title": it.title, "description": it.description} for it in existing]
            rows = [{"icon": i, "title": t, "description": d} for i, t, d in WHY_US_EXTRA]
            if not kept:
                kept = [{"icon": "fa-medal", "title": "Enterprise-grade Engineering", "description": "Senior engineers, code reviews and CI/CD on every delivery."}]
            _items(apps, section, kept + rows)
        elif section_type == "carousel":
            section.items = []
            section.save()
    # Move the legacy 24/7 SOC image band out of the main flow (kept, inactive)
    legacy = home.sections.filter(section_type="image").first()
    if legacy:
        legacy.sort_order = 200
        legacy.is_active = False
        legacy.save()

    # ---- 3. Carousel slides ----
    if not Slide.objects.exists():
        Slide.objects.create(
            title="Enterprise Software That Drives Growth",
            subtitle="Software & IT Solutions",
            description="From secure websites to full ERP platforms — we design, build and operate technology that moves your business forward.",
            primary_button_text="Explore Services", primary_button_url="/services/",
            secondary_button_text="Contact Us", secondary_button_url="/contact/",
            sort_order=10,
        )
        Slide.objects.create(
            title="Defend Your Business Around the Clock",
            subtitle="24/7 Cyber Security",
            description="Managed SOC monitoring, penetration testing and incident response from certified security engineers.",
            primary_button_text="Talk to an Expert", primary_button_url="/contact/",
            secondary_button_text="Our Services", secondary_button_url="/services/",
            sort_order=20,
        )
        Slide.objects.create(
            title="Cloud, AI & Automation — Built for Scale",
            subtitle="Cloud & DevOps",
            description="Kubernetes-native deployments, CI/CD pipelines and AI-powered automation that cut costs and ship faster.",
            primary_button_text="See Our Work", primary_button_url="/projects/",
            secondary_button_text="Get Pricing", secondary_button_url="/pricing/",
            sort_order=30,
        )

    # ---- 4. Services (icons + descriptions) ----
    service_updates = {
        "Web Development": ("fa-code", "Modern, secure websites and web applications built with Django, React and Next.js."),
        "Mobile Applications": ("fa-mobile-screen", "Cross-platform iOS & Android apps with Flutter and React Native."),
        "Cloud & DevOps": ("fa-cloud", "Cloud migration, Kubernetes, CI/CD pipelines and 24/7 infrastructure monitoring."),
    }
    for service in Service.objects.all():
        if service.name in service_updates:
            icon, desc = service_updates[service.name]
            service.icon = icon
            if not service.short_description:
                service.short_description = desc
            service.save()

    # ---- 5. Products ----
    if not Product.objects.exists():
        for name, item_type, icon, desc, keywords in PRODUCTS:
            Product.objects.create(
                name=name, slug=name.lower().replace(" ", "-").replace("&", "and"),
                item_type=item_type, icon=icon, short_description=desc, keywords=keywords,
                sort_order=Product.objects.count() + 1,
            )

    # ---- 6. Portfolio ----
    if not Project.objects.exists():
        for title, desc in PROJECTS:
            Project.objects.create(
                title=title, slug=title.lower().replace(" ", "-"), short_description=desc,
                sort_order=Project.objects.count() + 1,
            )

    # ---- 7. Testimonials ----
    if not Testimonial.objects.exists():
        for author, designation, quote in TESTIMONIALS:
            Testimonial.objects.create(author=author, designation=designation, quote=quote, sort_order=Testimonial.objects.count() + 1)

    # ---- 8. FAQs ----
    if not FAQ.objects.exists():
        for question, answer in FAQ_ITEMS:
            FAQ.objects.create(question=question, answer=answer, sort_order=FAQ.objects.count() + 1)

    # ---- 9. Team ----
    existing_team = {t.name for t in Team.objects.all()}
    for idx, (name, designation, bio) in enumerate(TEAM_EXTRA, start=10):
        if name not in existing_team:
            Team.objects.create(name=name, designation=designation, bio=bio, sort_order=idx)

    # ---- 10. Pricing ----
    for name, data in PRICING.items():
        plan, _ = Price.objects.get_or_create(name=name, defaults=data)
        for key, value in data.items():
            setattr(plan, key, value)
        plan.is_active = True
        plan.save()

    # ---- 11. Jobs ----
    existing_jobs = {j.title for j in Job.objects.all()}
    for idx, (title, location, job_type, experience, desc) in enumerate(JOBS_EXTRA, start=10):
        if title not in existing_jobs:
            Job.objects.create(title=title, slug=title.lower().replace(" ", "-"), location=location, job_type=job_type, experience=experience, description=desc, sort_order=idx)

    # ---- 12. Theme ----
    Theme.objects.update(is_active=False)
    theme, _ = Theme.objects.get_or_create(name="GFT Premium Theme")
    theme.primary_color = "#5b63ee"
    theme.secondary_color = "#0b1635"
    theme.font_family = "Inter, sans-serif"
    theme.is_active = True
    theme.save()

    # ---- 13. Contact map config ----
    if not MapCfg.objects.exists():
        MapCfg.objects.create(
            embed_url="https://www.google.com/maps?q=Sector%2062%2C%20Noida%2C%20Uttar%20Pradesh%20201301&output=embed",
            address="Sector 62, Noida, Uttar Pradesh 201301, India",
            phone="+91 8819981884",
            email="chcyberarmy@gmail.com",
        )

    # ---- 14. Navigation menus ----
    _menu(apps, "main", "Main Menu", [
        (10, "Home", "/", []),
        (20, "Services", "/services/", [
            (10, "Service Overview", "/services/"),
            (20, "Pricing Plans", "/pricing/"),
            (30, "FAQ", "/faq/"),
            (40, "Get a Quote", "/contact/"),
        ]),
        (30, "Solutions", "/services/", [
            (10, "Cyber Security", "/services/"),
            (20, "Cloud & DevOps", "/services/"),
            (30, "AI & Automation", "/services/"),
            (40, "ERP Solutions", "/services/"),
        ]),
        (40, "Products", "/", [
            (10, "All Products", "/"),
            (20, "Portfolio", "/projects/"),
            (30, "Pricing", "/pricing/"),
        ]),
        (50, "Industries", "/services/", [
            (10, "Education", "/services/"),
            (20, "Healthcare", "/services/"),
            (30, "FinTech", "/services/"),
            (40, "Government", "/services/"),
        ]),
        (60, "Resources", "/faq/", [
            (10, "FAQ", "/faq/"),
            (20, "Team", "/team/"),
            (30, "Projects", "/projects/"),
            (40, "Careers", "/career/"),
            (50, "Pricing", "/pricing/"),
        ]),
        (70, "Company", "/about/", [
            (10, "About Us", "/about/"),
            (20, "Team", "/team/"),
            (30, "Careers", "/career/"),
            (40, "Terms & Conditions", "/terms-and-conditions/"),
        ]),
        (80, "Contact Us", "/contact/", []),
    ])
    _menu(apps, "footer", "Footer Menu", [
        (10, "About", "/about/", []),
        (20, "Services", "/services/", []),
        (30, "Projects", "/projects/", []),
        (40, "Contact", "/contact/", []),
        (50, "Terms", "/terms-and-conditions/", []),
    ])

    # ---- 15. Footer sections ----
    link_sections = list(Footer.objects.filter(section_type="links").order_by("sort_order"))
    for section in Footer.objects.all():
        section.links.all().delete()
    if link_sections:
        company = link_sections[0]
        company.title = "Company"
        company.save()
        for sort, label, url in [(10, "About Us", "/about/"), (20, "Services", "/services/"), (30, "Projects", "/projects/"), (40, "Careers", "/career/"), (50, "Contact", "/contact/")]:
            FooterLink.objects.create(section=company, label=label, url=url, sort_order=sort)
        if len(link_sections) > 1:
            legal = link_sections[1]
            legal.title = "Legal"
            legal.save()
            FooterLink.objects.create(section=legal, label="Terms & Conditions", url="/terms-and-conditions/", sort_order=10)
            FooterLink.objects.create(section=legal, label="Contact", url="/contact/", sort_order=20)
    contact_footer = Footer.objects.filter(section_type="contact").first()
    if contact_footer:
        contact_footer.content = "Sector 62, Noida, Uttar Pradesh 201301, India\n+91 8819981884\nchcyberarmy@gmail.com"
        contact_footer.save()
    newsletter_footer = Footer.objects.filter(section_type="newsletter").first()
    if newsletter_footer:
        newsletter_footer.content = "Product updates, security tips and company news. No spam."
        newsletter_footer.save()


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0018_contactmapconfig_headermenu_headermenuitem"),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
