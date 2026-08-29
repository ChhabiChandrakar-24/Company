from django.urls import path
from crm import views

urlpatterns = [
    # Inquiries
    path("inquiries/", views.inquiry_list, name="inquiry-list"),
    path("inquiries/create/", views.inquiry_create, name="inquiry-create"),
    path("inquiries/<int:inquiry_id>/edit/", views.inquiry_edit, name="inquiry-edit"),
    path("inquiries/<int:inquiry_id>/delete/", views.inquiry_delete, name="inquiry-delete"),
    path("inquiries/<int:inquiry_id>/update-status/", views.inquiry_update_status, name="inquiry-update-status"),
    
    # Timeline
    path("clients/<int:client_id>/timeline/", views.client_timeline, name="client-timeline"),
    
    # Sub-entities creation/linking
    path("inquiries/<int:inquiry_id>/add-requirement/", views.add_requirement, name="crm-add-requirement"),
    path("inquiries/<int:inquiry_id>/add-quotation/", views.add_quotation, name="crm-add-quotation"),
    path("inquiries/<int:inquiry_id>/add-payment/", views.add_payment, name="crm-add-payment"),
    path("inquiries/<int:inquiry_id>/add-communication/", views.add_communication, name="crm-add-communication"),
    path("inquiries/<int:inquiry_id>/link-project/", views.link_project, name="crm-link-project"),
    path("inquiries/<int:inquiry_id>/link-meeting/", views.link_meeting, name="crm-link-meeting"),

    # Advanced Client Requirement Management
    path("inquiries/<int:inquiry_id>/requirements/create/", views.requirement_create, name="crm-requirement-create"),
    path("requirements/<int:req_id>/edit/", views.requirement_edit, name="crm-requirement-edit"),
    path("requirements/<int:req_id>/", views.requirement_detail, name="crm-requirement-detail"),
    path("requirements/<int:req_id>/comment/", views.add_requirement_comment, name="crm-requirement-comment"),

    # Client Scheduler
    path("inquiries/<int:inquiry_id>/schedule-meeting/", views.schedule_client_meeting, name="crm-schedule-meeting"),

    # One-click Secure Client Portal Access
    path("clients/<int:client_id>/access/<str:action_type>/", views.update_portal_access, name="crm-client-portal-access"),
    path("portal/login/<str:uidb64>/<str:token>/", views.client_token_login, name="crm-client-token-login"),
    path("portal/", views.client_portal_dashboard, name="crm-client-portal-dashboard"),

    # Phase 8 URLs
    path("dashboard/", views.crm_dashboard, name="crm-dashboard"),
    
    path("companies/", views.company_list, name="company-list"),
    path("companies/create/", views.company_create, name="company-create"),
    path("companies/<int:company_id>/", views.company_detail, name="company-detail"),
    
    path("deals/", views.deal_pipeline, name="deal-pipeline"),
    path("inquiries/<int:inquiry_id>/convert/", views.convert_to_deal, name="convert-to-deal"),
    
    path("inquiries/<int:inquiry_id>/add-task/", views.add_crm_task, name="crm-add-task"),
]

