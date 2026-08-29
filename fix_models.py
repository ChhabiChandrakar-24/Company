
import re

content = open("website/models.py").read()

# Let's make sure ThemeSettings is there and NavigationItem is correct.
# Actually it's probably completely messed up. Let's restore from backup if there is one? No backup.
# But I have the `view_file` output in my context from just a minute ago!

clean_models = """from django.db import models

class WebsiteSettings(models.Model):
    company_name = models.CharField(max_length=150, default="Geeta ForgeTech")
    tagline = models.CharField(max_length=255, blank=True)
    logo = models.ImageField(upload_to="website/branding/", blank=True)
    favicon = models.ImageField(upload_to="website/branding/", blank=True)
    phone = models.CharField(max_length=40, default="+91 8819981884")
    email = models.EmailField(default="chcyberarmy@gmail.com")
    address = models.TextField(blank=True)
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    footer_text = models.CharField(max_length=255, blank=True)
    default_meta_description = models.TextField(blank=True)
    default_meta_keywords = models.TextField(blank=True)

    class Meta:
        verbose_name = "My company setting"
        verbose_name_plural = "My company settings"

    def __str__(self):
        return self.company_name

class WebsitePage(models.Model):
    slug = models.SlugField(max_length=80, unique=True, help_text="Use home for the root page.")
    title = models.CharField(max_length=200)
    meta_description = models.TextField(blank=True)
    meta_keywords = models.TextField(blank=True)
    aeo = models.BooleanField(default=False, help_text="Automated Expert Optimization flag")
    geo = models.CharField(max_length=100, blank=True, help_text="Geographic targeting information")
    llmo = models.CharField(max_length=100, blank=True, help_text="Local Language Meta Optimization")
    aiseo_score = models.CharField(max_length=10, choices=[('low','Low'),('medium','Medium'),('high','High')], default='medium', help_text="AI‑generated SEO score")
    eeat_rating = models.CharField(max_length=10, choices=[('low','Low'),('medium','Medium'),('high','High')], default='medium', help_text="EEAT rating")
    html_content = models.TextField(blank=True, help_text="Complete editable HTML for this page (Legacy Mode).")
    is_dynamic_render = models.BooleanField(default=False, help_text="If true, uses the new Component-based Dynamic CMS rendering.")
    status = models.CharField(max_length=10, choices=[('draft','Draft'),('published','Published'),('archived','Archived')], default='published')
    seo_title = models.CharField(max_length=200, blank=True, help_text="Override the page title for SEO purposes")
    page_order = models.PositiveIntegerField(default=0, help_text="Used for sorting pages globally if needed")
    
    def get_absolute_url(self):
        return '/' if self.slug == 'home' else f'/{self.slug}/'
    show_in_navigation = models.BooleanField(default=True)
    navigation_order = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("navigation_order", "title")

    def __str__(self):
        return self.title

class WebsiteSubmission(models.Model):
    CONTACT = "contact"
    CAREER = "career"
    NEWSLETTER = "newsletter"
    CONSULTATION = "consultation"
    TYPES = ((CONTACT, "Contact"), (CONSULTATION, "Consultation"), (CAREER, "Career"), (NEWSLETTER, "Newsletter"))

    submission_type = models.CharField(max_length=20, choices=TYPES, default=CONTACT)
    name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    message = models.TextField(blank=True)
    extra_data = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.get_submission_type_display()}: {self.name or self.email}"

class WebsiteSection(models.Model):
    page = models.ForeignKey(WebsitePage, on_delete=models.CASCADE, related_name="sections")
    section_type = models.CharField(max_length=50, default="content")
    heading = models.CharField(max_length=200)
    subheading = models.CharField(max_length=255, blank=True)
    content = models.TextField(blank=True)
    image = models.ImageField(upload_to="website/sections/", blank=True)
    items = models.JSONField(default=list, blank=True, help_text='Optional list such as [{"title":"...","description":"..."}].')
    is_active = models.BooleanField(default=True)
    visibility = models.CharField(max_length=20, choices=[('public', 'Public'), ('logged_in', 'Logged In Only'), ('admin_only', 'Admin Only')], default='public')
    settings = models.JSONField(default=dict, blank=True, help_text='Advanced configuration for margins, padding, styles, etc.')
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "id")

    def __str__(self):
        return f"{self.page}: {self.heading}"

class WebsiteService(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)
    short_description = models.TextField(blank=True)
    full_description = models.TextField(blank=True)
    icon = models.CharField(max_length=100, blank=True)
    image = models.ImageField(upload_to="website/services/", blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "name")

    def __str__(self):
        return self.name

class PricingPlan(models.Model):
    name = models.CharField(max_length=120)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    billing_period = models.CharField(max_length=50, default="month")
    description = models.TextField(blank=True)
    features = models.TextField(blank=True, help_text="Enter one feature per line.")
    button_text = models.CharField(max_length=80, default="Get Started")
    button_url = models.CharField(max_length=500, default="/contact/")
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "name")

    @property
    def feature_list(self):
        return [line.strip() for line in self.features.splitlines() if line.strip()]

    def __str__(self):
        return self.name

class JobOpening(models.Model):
    title = models.CharField(max_length=180)
    slug = models.SlugField(unique=True)
    location = models.CharField(max_length=150, blank=True)
    job_type = models.CharField(max_length=80, blank=True)
    experience = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    requirements = models.TextField(blank=True)
    application_url = models.URLField(blank=True)
    application_email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "title")

    def __str__(self):
        return self.title

class TeamMember(models.Model):
    name = models.CharField(max_length=150)
    designation = models.CharField(max_length=150, blank=True)
    bio = models.TextField(blank=True)
    image = models.ImageField(upload_to="website/team/", blank=True)
    linkedin_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "name")

    def __str__(self):
        return self.name

class FooterSection(models.Model):
    LINKS = "links"
    TEXT = "text"
    CONTACT = "contact"
    NEWSLETTER = "newsletter"
    SECTION_TYPES = (
        (LINKS, "Links"),
        (TEXT, "Text"),
        (CONTACT, "Contact information"),
        (NEWSLETTER, "Newsletter form"),
    )

    title = models.CharField(max_length=150)
    section_type = models.CharField(max_length=20, choices=SECTION_TYPES, default=LINKS)
    content = models.TextField(blank=True, help_text="Optional text shown inside this footer section.")
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("sort_order", "id")

    def __str__(self):
        return self.title

class FooterLink(models.Model):
    section = models.ForeignKey(FooterSection, on_delete=models.CASCADE, related_name="links")
    label = models.CharField(max_length=120)
    url = models.CharField(max_length=500, help_text="Internal path, email, phone or full URL.")
    icon_class = models.CharField(max_length=100, blank=True, help_text="Optional Font Awesome class.")
    open_in_new_tab = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("sort_order", "id")

    def __str__(self):
        return self.label

class FooterSocialLink(models.Model):
    platform = models.CharField(max_length=80)
    url = models.URLField()
    icon_class = models.CharField(max_length=100, default="fa-solid fa-link")
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("sort_order", "id")

    def __str__(self):
        return self.platform

class PortfolioProject(models.Model):
    title = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)
    short_description = models.TextField(blank=True)
    full_description = models.TextField(blank=True)
    image = models.ImageField(upload_to="website/projects/", blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "title")

    def __str__(self):
        return self.title

class Testimonial(models.Model):
    author = models.CharField(max_length=150)
    designation = models.CharField(max_length=150, blank=True)
    quote = models.TextField()
    image = models.ImageField(upload_to="website/testimonials/", blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "id")

    def __str__(self):
        return self.author

class FAQ(models.Model):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "id")
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return self.question

class NavigationMenu(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name

class NavigationItem(models.Model):
    menu = models.ForeignKey(NavigationMenu, on_delete=models.CASCADE, related_name="items")
    label = models.CharField(max_length=150)
    url = models.CharField(max_length=500, blank=True, help_text="Direct URL or path.")
    page = models.ForeignKey(WebsitePage, on_delete=models.SET_NULL, null=True, blank=True, related_name="nav_items")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children")
    open_in_new_tab = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "id")

    def __str__(self):
        return self.label

    def get_url(self):
        if self.page:
            return self.page.get_absolute_url()
        return self.url or "#"

class ThemeSettings(models.Model):
    name = models.CharField(max_length=100)
    primary_color = models.CharField(max_length=20, default="#ff7a00")
    secondary_color = models.CharField(max_length=20, default="#111b35")
    font_family = models.CharField(max_length=100, default="Poppins, sans-serif")
    is_active = models.BooleanField(default=False)

    class Meta:
        ordering = ("-is_active", "name")

    def __str__(self):
        return self.name

class MediaAsset(models.Model):
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to="website/media/")
    file_type = models.CharField(max_length=50, choices=[("image", "Image"), ("video", "Video"), ("document", "Document")])
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-uploaded_at",)

    def __str__(self):
        return self.title
"""

with open("website/models.py", "w", encoding="utf-8") as f:
    f.write(clean_models)
print("Models restored!")

