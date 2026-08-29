import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


def login(client, username, password):
    response = client.post('/login/', {'username': username, 'password': password})
    assert response.status_code in (302, 200), f'Login failed: {response.status_code}'
    return client


def run_e2e():
    client = Client()
    # Ensure admin user exists
    admin, created = User.objects.get_or_create(username='admin', defaults={'is_staff': True, 'is_superuser': True})
    if created:
        admin.set_password('admin123')
        admin.save()
    # Admin login
    login(client, 'admin', 'admin123')

    # ---- CMS: Create Page ----
    create_page_url = reverse('websitepage-list')  # DRF viewset name
    page_data = {
        'title': 'Test Page',
        'slug': 'test-page',
        'status': 'draft',
        'seo_title': 'Test SEO',
        'meta_description': 'Test meta',
    }
    resp = client.post(create_page_url, page_data, content_type='application/json')
    assert resp.status_code == 201, f'Create page failed: {resp.status_code}'
    page_id = resp.json()['id']

    # Add Section
    add_section_url = reverse('websitesection-list')
    section_data = {
        'page': page_id,
        'section_type': 'text',
        'content': 'Hello World',
        'display_order': 1,
        'visibility': True,
    }
    resp = client.post(add_section_url, section_data, content_type='application/json')
    assert resp.status_code == 201, f'Add section failed: {resp.status_code}'
    # Publish page via custom action
    publish_url = reverse('websitepage-publish', args=[page_id])
    resp = client.post(publish_url)
    assert resp.status_code == 200, f'Publish failed: {resp.status_code}'

    # Verify public page accessible (no auth)
    public_client = Client()
    public_resp = public_client.get(f'/pages/{"test-page"}/')
    assert public_resp.status_code == 200, f'Public page not visible: {public_resp.status_code}'

    # ---- Navigation: Update Menu ----
    nav_url = reverse('navigationmenu-list')
    nav_data = {'name': 'Main', 'position': 1}
    resp = client.post(nav_url, nav_data, content_type='application/json')
    assert resp.status_code == 201, f'Create menu failed: {resp.status_code}'
    menu_id = resp.json()['id']
    # Add item
    item_url = reverse('navigationitem-list')
    item_data = {'menu': menu_id, 'title': 'Test', 'url': '/test-page/', 'order': 1}
    resp = client.post(item_url, item_data, content_type='application/json')
    assert resp.status_code == 201, f'Add nav item failed: {resp.status_code}'
    # Verify navigation appears on public page
    public_resp = public_client.get(f'/pages/{"test-page"}/')
    assert b'Test' in public_resp.content, 'Navigation item not rendered'

    # ---- Theme: User selects dark mode ----
    user, created = User.objects.get_or_create(username='user', defaults={'is_staff': False, 'is_superuser': False})
    if created:
        user.set_password('user123')
        user.save()
    client.logout()
    login(client, 'user', 'user123')
    theme_url = '/api/theme/'
    resp = client.post(theme_url, {'mode': 'dark'}, content_type='application/json')
    assert resp.status_code == 200, f'Set theme failed: {resp.status_code}'
    client.logout()
    login(client, 'user', 'user123')
    resp = client.get('/')
    assert b'dark' in resp.content.lower(), 'Dark theme not applied'

    # ---- CRM Lead flow ----
    inquiry_url = reverse('inquiry-list')
    lead_data = {'title': 'Lead X', 'status': 'new'}
    resp = client.post(inquiry_url, lead_data, content_type='application/json')
    assert resp.status_code == 201, f'Create lead failed: {resp.status_code}'
    lead_id = resp.json()['id']
    # Assign
    resp = client.patch(inquiry_url + f'{lead_id}/', {'assignee_id': user.id}, content_type='application/json')
    assert resp.status_code in (200, 204), f'Assign lead failed: {resp.status_code}'
    # Follow‑up (add task)
    task_url = reverse('add-crm-task', args=[lead_id])
    resp = client.post(task_url, {'title': 'Call client', 'due_date': '2026-09-01'}, content_type='application/json')
    assert resp.status_code in (200, 302), f'Add task failed: {resp.status_code}'
    # Convert to Deal
    convert_url = reverse('convert-to-deal', args=[lead_id])
    resp = client.post(convert_url)
    assert resp.status_code in (200, 302), f'Convert to deal failed: {resp.status_code}'
    # Pipeline view
    pipeline_url = reverse('deal-pipeline')
    resp = client.get(pipeline_url)
    assert resp.status_code == 200, f'Deal pipeline view failed: {resp.status_code}'
    # Dashboard view
    dash_url = reverse('crm-dashboard')
    resp = client.get(dash_url)
    assert resp.status_code == 200, f'Dashboard view failed: {resp.status_code}'

    print('All E2E steps passed')

if __name__ == '__main__':
    run_e2e()
