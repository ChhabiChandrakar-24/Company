
with open("website/models.py", "a", encoding="utf-8") as f:
    f.write("""

class PortfolioProject(models.Model):
    title = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)
    short_description = models.TextField(blank=True)
    full_description = models.TextField(blank=True)
    image = models.ImageField(upload_to=\"website/projects/\", blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = (\"sort_order\", \"title\")

    def __str__(self):
        return self.title


class Testimonial(models.Model):
    author = models.CharField(max_length=150)
    designation = models.CharField(max_length=150, blank=True)
    quote = models.TextField()
    image = models.ImageField(upload_to=\"website/testimonials/\", blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = (\"sort_order\", \"id\")

    def __str__(self):
        return self.author


class FAQ(models.Model):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = (\"sort_order\", \"id\")
        verbose_name = \"FAQ\"
        verbose_name_plural = \"FAQs\"

    def __str__(self):
        return self.question
""")

