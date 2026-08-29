import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chhabi.settings')
django.setup()

with connection.cursor() as cursor:
    # 1. Create Privacy Policy Page
    cursor.execute("""
        INSERT INTO website_websitepage (slug, title, meta_description, meta_keywords, aeo, geo, llmo, aiseo_score, eeat_rating, html_content, is_dynamic_render, status, seo_title, page_order, show_in_navigation, navigation_order, updated_at, additional_keywords, canonical_url, focus_keyword, social_description, social_image, social_title)
        VALUES ('privacy-policy', 'Privacy Policy', '', '', 0, '', '', 'medium', 'medium', '', 1, 'published', 'Privacy Policy - Horilla', 0, 1, 0, NOW(), '', '', '', '', '', '')
        ON DUPLICATE KEY UPDATE title='Privacy Policy'
    """)
    cursor.execute("SELECT id FROM website_websitepage WHERE slug='privacy-policy'")
    privacy_page_id = cursor.fetchone()[0]

    # Delete existing sections
    cursor.execute("DELETE FROM website_websitesection WHERE page_id = %s", [privacy_page_id])

    # Create Policy Section
    cursor.execute("""
        INSERT INTO website_websitesection (page_id, section_type, heading, subheading, content, image, items, is_active, visibility, settings, sort_order, primary_button_text, primary_button_url, secondary_button_text, secondary_button_url)
        VALUES (%s, 'policy', 'Privacy Policy', 'Last updated: August 28, 2026', 'We respect your privacy and are committed to protecting your personal data.', '', '[]', 1, 'public', '{}', 0, '', '', '', '')
    """, [privacy_page_id])
    privacy_section_id = cursor.lastrowid

    # Create Policy Items
    cursor.execute("""
        INSERT INTO website_websitesectionitem (section_id, title, subtitle, description, value, image, icon, button_text, button_url, sort_order, is_active)
        VALUES (%s, '1. Information We Collect', '', 'We collect information you provide directly to us.', '', '', '', '', '', 1, 1)
    """, [privacy_section_id])
    
    cursor.execute("""
        INSERT INTO website_websitesectionitem (section_id, title, subtitle, description, value, image, icon, button_text, button_url, sort_order, is_active)
        VALUES (%s, '2. How We Use Your Information', '', 'We use the information we collect to provide our services.', '', '', '', '', '', 2, 1)
    """, [privacy_section_id])

    # 2. Create Terms & Conditions Page
    cursor.execute("""
        INSERT INTO website_websitepage (slug, title, meta_description, meta_keywords, aeo, geo, llmo, aiseo_score, eeat_rating, html_content, is_dynamic_render, status, seo_title, page_order, show_in_navigation, navigation_order, updated_at, additional_keywords, canonical_url, focus_keyword, social_description, social_image, social_title)
        VALUES ('terms-conditions', 'Terms & Conditions', '', '', 0, '', '', 'medium', 'medium', '', 1, 'published', 'Terms & Conditions - Horilla', 0, 1, 0, NOW(), '', '', '', '', '', '')
        ON DUPLICATE KEY UPDATE title='Terms & Conditions'
    """)
    cursor.execute("SELECT id FROM website_websitepage WHERE slug='terms-conditions'")
    terms_page_id = cursor.fetchone()[0]

    cursor.execute("DELETE FROM website_websitesection WHERE page_id = %s", [terms_page_id])

    cursor.execute("""
        INSERT INTO website_websitesection (page_id, section_type, heading, subheading, content, image, items, is_active, visibility, settings, sort_order, primary_button_text, primary_button_url, secondary_button_text, secondary_button_url)
        VALUES (%s, 'policy', 'Terms & Conditions', 'Last updated: August 28, 2026', 'Please read these terms carefully.', '', '[]', 1, 'public', '{}', 0, '', '', '', '')
    """, [terms_page_id])
    terms_section_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO website_websitesectionitem (section_id, title, subtitle, description, value, image, icon, button_text, button_url, sort_order, is_active)
        VALUES (%s, '1. Acceptance of Terms', '', 'By accessing the Service, you agree to these Terms.', '', '', '', '', '', 1, 1)
    """, [terms_section_id])

    # 3. Add to Footer Navigation
    cursor.execute("SELECT id FROM website_navigationmenu WHERE slug='footer'")
    footer_row = cursor.fetchone()
    if not footer_row:
        cursor.execute("INSERT INTO website_navigationmenu (name, slug, is_active) VALUES ('Footer Menu', 'footer', 1)")
        footer_menu_id = cursor.lastrowid
    else:
        footer_menu_id = footer_row[0]

    cursor.execute("DELETE FROM website_navigationitem WHERE menu_id = %s AND label IN ('Privacy Policy', 'Terms & Conditions')", [footer_menu_id])

    cursor.execute("""
        INSERT INTO website_navigationitem (menu_id, label, url, page_id, open_in_new_tab, sort_order, is_active)
        VALUES (%s, 'Privacy Policy', '', %s, 0, 90, 1)
    """, [footer_menu_id, privacy_page_id])

    cursor.execute("""
        INSERT INTO website_navigationitem (menu_id, label, url, page_id, open_in_new_tab, sort_order, is_active)
        VALUES (%s, 'Terms & Conditions', '', %s, 0, 91, 1)
    """, [footer_menu_id, terms_page_id])

print("Generated using raw SQL successfully!")
