"""
chhabi/config.py

Chhabi app configurations
"""

import importlib
import logging

from django.apps import apps
from django.conf import settings
from django.contrib.auth.context_processors import PermWrapper
from django.urls import NoReverseMatch

from chhabi.chhabi_apps import SIDEBARS

logger = logging.getLogger(__name__)


def get_apps_in_base_dir():
    return SIDEBARS


def import_method(accessibility):
    module_path, method_name = accessibility.rsplit(".", 1)
    module = __import__(module_path, fromlist=[method_name])
    accessibility_method = getattr(module, method_name)
    return accessibility_method


ALL_MENUS = {}

SIDEBAR_CATEGORIES = (
    ("HRM", {"employee", "recruitment", "onboarding", "attendance", "leave", "payroll", "pms", "offboarding"}),
    ("CRM & Sales", {"crm", "quotations"}),
    ("Work & Operations", {"project", "live_meeting", "helpdesk", "asset"}),
    ("Insights", {"report"}),
)


def group_sidebar_menus(menus):
    """Group only the menus already permitted for the current request."""
    remaining = list(menus or [])
    groups = []
    for label, apps_in_category in SIDEBAR_CATEGORIES:
        category_menus = [menu for menu in remaining if menu.get("app") in apps_in_category]
        if category_menus:
            groups.append({"label": label, "menus": category_menus})
            remaining = [menu for menu in remaining if menu.get("app") not in apps_in_category]
    if remaining:
        groups.append({"label": "More", "menus": remaining})
    return groups


def sidebar(request):

    base_dir_apps = get_apps_in_base_dir()

    if not request.user.is_anonymous:
        request.MENUS = []
        MENUS = request.MENUS

        for app in base_dir_apps:
            if apps.is_installed(app):
                try:
                    sidebar = importlib.import_module(app + ".sidebar")

                except Exception as e:
                    logger.error(e)
                    continue

                if sidebar:
                    accessibility = None
                    if getattr(sidebar, "ACCESSIBILITY", None):
                        accessibility = import_method(sidebar.ACCESSIBILITY)

                    if not accessibility or accessibility(
                        request,
                        sidebar.MENU,
                        PermWrapper(request.user),
                    ):
                        MENU = {}
                        MENU["menu"] = sidebar.MENU
                        MENU["app"] = app
                        MENU["img_src"] = sidebar.IMG_SRC
                        MENU["submenu"] = []
                        MENUS.append(MENU)
                        for source_submenu in sidebar.SUBMENUS:
                            # Do not mutate the module-level menu definition: it is
                            # reused by every request.
                            submenu = source_submenu.copy()

                            accessibility = None

                            if submenu.get("accessibility"):
                                accessibility = import_method(submenu["accessibility"])
                            try:
                                # Some add-ons use reverse_lazy() for their menu
                                # URL. If an optional add-on route is unavailable,
                                # omit only that menu item instead of failing the
                                # complete dashboard render.
                                redirect = str(submenu["redirect"])
                            except NoReverseMatch:
                                logger.warning(
                                    "Skipping sidebar menu '%s': its URL is unavailable.",
                                    submenu.get("menu", ""),
                                )
                                continue
                            redirect = redirect.split("?")
                            submenu["redirect"] = redirect[0]

                            if not accessibility or accessibility(
                                request,
                                submenu,
                                PermWrapper(request.user),
                            ):
                                MENU["submenu"].append(submenu)
        ALL_MENUS[request.session.session_key] = MENUS


def get_MENUS(request):
    ALL_MENUS[request.session.session_key] = []
    if getattr(request, "user", None) and hasattr(request.user, "crm_client_profile"):
        # Customize sidebar navigation specifically for authenticated client portal users
        portal_menu = [{
            "menu": "Client Workspace",
            "app": "crm",
            "img_src": "images/ui/recruitment.png",
            "submenu": [
                {
                    "menu": "Dashboard",
                    "redirect": "/crm/portal/",
                }
            ]
        }]
        return {
            "sidebar": portal_menu,
            "sidebar_groups": [{"label": "CRM & Sales", "menus": portal_menu}],
        }

    sidebar(request)
    menus = ALL_MENUS.get(request.session.session_key) or []
    return {"sidebar": menus, "sidebar_groups": group_sidebar_menus(menus)}
