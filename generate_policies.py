import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chhabi.settings')
django.setup()

from website.models import WebsitePage, WebsiteSection, WebsiteSectionItem, NavigationMenu, NavigationItem

# 1. Create Privacy Policy Page
privacy_page, _ = WebsitePage.objects.get_or_create(
    slug='privacy-policy',
    defaults={
        'title': 'Privacy Policy',
        'is_dynamic_render': True,
        'status': 'published',
        'seo_title': 'Privacy Policy - Horilla',
    }
)

# Clear existing sections if running multiple times
privacy_page.sections.all().delete()

# Create Policy Section
privacy_section = WebsiteSection.objects.create(
    page=privacy_page,
    section_type='policy',
    heading='Privacy Policy',
    subheading='Last updated: August 28, 2026',
    content='We respect your privacy and are committed to protecting your personal data.',
    primary_button_text='',
    primary_button_url='',
    secondary_button_text='',
    secondary_button_url=''
)

# Create Policy Items (Clauses)
WebsiteSectionItem.objects.create(
    section=privacy_section,
    title='1. Information We Collect',
    description='We collect information you provide directly to us, such as when you create or modify your account.',
    sort_order=1,
    value='', image='', icon='', button_text='', button_url=''
)

WebsiteSectionItem.objects.create(
    section=privacy_section,
    title='2. How We Use Your Information',
    description='We use the information we collect to provide, maintain, and improve our services.',
    sort_order=2,
    value='', image='', icon='', button_text='', button_url=''
)

# 2. Create Terms & Conditions Page
terms_page, _ = WebsitePage.objects.get_or_create(
    slug='terms-conditions',
    defaults={
        'title': 'Terms & Conditions',
        'is_dynamic_render': True,
        'status': 'published',
        'seo_title': 'Terms & Conditions - Horilla',
    }
)

terms_page.sections.all().delete()

terms_section = WebsiteSection.objects.create(
    page=terms_page,
    section_type='policy',
    heading='Terms & Conditions',
    subheading='Last updated: August 28, 2026',
    content='Please read these terms and conditions carefully before using our service.',
    primary_button_text='',
    primary_button_url='',
    secondary_button_text='',
    secondary_button_url=''
)

WebsiteSectionItem.objects.create(
    section=terms_section,
    title='1. Acceptance of Terms',
    description='By accessing or using the Service, you agree to be bound by these Terms.',
    sort_order=1,
    value='', image='', icon='', button_text='', button_url=''
)

# 3. Add to Footer Navigation
footer_menu, _ = NavigationMenu.objects.get_or_create(
    slug='footer',
    defaults={'name': 'Footer Menu'}
)

# Delete existing legal links to prevent duplicates
NavigationItem.objects.filter(menu=footer_menu, label__in=['Privacy Policy', 'Terms & Conditions']).delete()

NavigationItem.objects.create(
    menu=footer_menu,
    label='Privacy Policy',
    page=privacy_page,
    url='',
    sort_order=90
)

NavigationItem.objects.create(
    menu=footer_menu,
    label='Terms & Conditions',
    page=terms_page,
    url='',
    sort_order=91
)

print('Policies and footer links successfully generated.')
