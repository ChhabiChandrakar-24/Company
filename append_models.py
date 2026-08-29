
import os

new_models = """

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
    
    # Uploaded by could be a User FK, but leaving simple for now as requested.

    class Meta:
        ordering = ("-uploaded_at",)

    def __str__(self):
        return self.title
"""

with open("website/models.py", "a", encoding="utf-8") as f:
    f.write(new_models)
print("Models appended.")

