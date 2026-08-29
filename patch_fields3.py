with open('website/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

replacement = '''    visibility = models.CharField(max_length=20, choices=[('public', 'Public'), ('logged_in', 'Logged In Only'), ('admin_only', 'Admin Only')], default='public')
    settings = models.JSONField(default=dict, blank=True, help_text='Advanced configuration for margins, padding, styles, etc.')
    primary_button_text = models.CharField(max_length=80, blank=True, default="")
    primary_button_url = models.CharField(max_length=500, blank=True, default="")
    secondary_button_text = models.CharField(max_length=80, blank=True, default="")
    secondary_button_url = models.CharField(max_length=500, blank=True, default="")
    sort_order = models.PositiveIntegerField(default=0)'''

content = content.replace('''    visibility = models.CharField(max_length=20, choices=[('public', 'Public'), ('logged_in', 'Logged In Only'), ('admin_only', 'Admin Only')], default='public')
    settings = models.JSONField(default=dict, blank=True, help_text='Advanced configuration for margins, padding, styles, etc.')
    sort_order = models.PositiveIntegerField(default=0)''', replacement)

replacement2 = '''    open_in_new_tab = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)'''

content = content.replace('''    open_in_new_tab = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)''', replacement2)

with open('website/models.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Patched section buttons and nav item is_active!")
