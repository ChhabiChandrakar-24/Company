from django.contrib.auth.context_processors import PermWrapper
from django.urls import reverse
from django.utils.translation import gettext_lazy as trans

MENU = trans("CRM")
IMG_SRC = "images/ui/recruitment.png"
ACCESSIBILITY = "crm.sidebar.menu_accessibility"

SUBMENUS = [
    {
        "menu": trans("Dashboard"),
        "redirect": reverse("crm-dashboard"),
        "accessibility": "crm.sidebar.pipeline_accessibility",
    },
    {
        "menu": trans("Leads Pipeline"),
        "redirect": reverse("inquiry-list"),
        "accessibility": "crm.sidebar.pipeline_accessibility",
    },
    {
        "menu": trans("Deals Pipeline"),
        "redirect": reverse("deal-pipeline"),
        "accessibility": "crm.sidebar.pipeline_accessibility",
    },
    {
        "menu": trans("Companies"),
        "redirect": reverse("company-list"),
        "accessibility": "crm.sidebar.pipeline_accessibility",
    },
]

def menu_accessibility(request, _menu: str = "", user_perms: PermWrapper = [], *args, **kwargs) -> bool:
    user = request.user
    return user.is_superuser or user.has_perm("crm.view_inquiry")

def pipeline_accessibility(request, submenu, user_perms, *args, **kwargs):
    user = request.user
    return user.is_superuser or user.has_perm("crm.view_inquiry")
