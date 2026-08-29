"""URL configuration for the quotations app.

Provides basic routes for listing quotations and creating a new one.
"""

from django.urls import path
from . import views

urlpatterns = [
    path("", views.quotation_list, name="quotation-list"),
    path("<str:number>/", views.quotation_detail, name="quotation-detail"),
]
