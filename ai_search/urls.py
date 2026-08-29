from django.urls import path
from . import views
from . import api_views

app_name = 'ai_search'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('websites/', views.website_list, name='website_list'),
    path('websites/add/', views.add_website, name='add_website'),
    path('websites/<int:website_id>/', views.website_detail, name='website_detail'),
    path('websites/<int:website_id>/scan/', views.start_scan, name='start_scan'),
    path('scans/<int:scan_id>/', views.scan_detail, name='scan_detail'),
    path('issues/', views.issue_list, name='issue_list'),
    path('recommendations/', views.recommendation_list, name='recommendation_list'),
    
    # API endpoints
    path('api/websites/<int:website_id>/history/', api_views.WebsiteScanHistoryAPI.as_view(), name='api_scan_history'),
]
