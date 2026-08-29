with open('website/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'class WebsiteSectionItem' not in content:
    content += '''
from django.core.exceptions import ValidationError

class WebsiteSectionItem(models.Model):
    section = models.ForeignKey(WebsiteSection, on_delete=models.CASCADE, related_name="section_items")
    title = models.CharField(max_length=180)
    subtitle = models.CharField(max_length=180, blank=True)
    description = models.TextField(blank=True)
    value = models.CharField(max_length=80, blank=True, help_text="Useful for statistics, e.g. 250+.")
    image = models.ImageField(upload_to="website/section-items/", blank=True)
    icon = models.CharField(max_length=100, blank=True, help_text="Optional Font Awesome class.")
    button_text = models.CharField(max_length=80, blank=True)
    button_url = models.CharField(max_length=500, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("sort_order", "id")

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        if bool(self.button_text) != bool(self.button_url):
            raise ValidationError("Button text and URL must be provided together.")
'''

if 'class CarouselSlide' not in content:
    content += '''
class CarouselSlide(models.Model):
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=220, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="website/carousel/", blank=True)
    primary_button_text = models.CharField(max_length=80, blank=True)
    primary_button_url = models.CharField(max_length=500, blank=True)
    secondary_button_text = models.CharField(max_length=80, blank=True)
    secondary_button_url = models.CharField(max_length=500, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("sort_order", "id")

    def __str__(self):
        return self.title
'''

if 'class WebsiteProduct' not in content:
    content += '''
class WebsiteProduct(models.Model):
    name = models.CharField(max_length=160)
    slug = models.SlugField(unique=True)
    item_type = models.CharField(max_length=20, choices=[('product', 'Product'), ('solution', 'Solution')], default='solution')
    short_description = models.TextField(blank=True)
    full_description = models.TextField(blank=True)
    image = models.ImageField(upload_to="website/products/", blank=True)
    icon = models.CharField(max_length=100, blank=True)
    keywords = models.CharField(max_length=500, blank=True)
    button_text = models.CharField(max_length=80, default="Learn more")
    button_url = models.CharField(max_length=500, default="/contact/")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "name")

    def __str__(self):
        return self.name
'''

with open('website/models.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Models updated!')
