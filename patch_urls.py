import os

filepath = 'crm/urls.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

new_urls = """
    # Phase 8 URLs
    path("dashboard/", views.crm_dashboard, name="crm-dashboard"),
    
    path("companies/", views.company_list, name="company-list"),
    path("companies/create/", views.company_create, name="company-create"),
    path("companies/<int:company_id>/", views.company_detail, name="company-detail"),
    
    path("deals/", views.deal_pipeline, name="deal-pipeline"),
    path("inquiries/<int:inquiry_id>/convert/", views.convert_to_deal, name="convert-to-deal"),
    
    path("inquiries/<int:inquiry_id>/add-task/", views.add_crm_task, name="crm-add-task"),
]
"""
content = content.replace("]", new_urls)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
