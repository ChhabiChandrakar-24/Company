from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as trans


MENU = trans("Live Meetings")
IMG_SRC = "images/ui/pms.svg"

SUBMENUS = [
    {
        "menu": trans("All Meetings"),
        "redirect": reverse_lazy("view-meetings"),
    },
    {
        "menu": trans("Create Meeting"),
        "redirect": reverse_lazy("create-meeting-shortcut"),
    },
    {
        "menu": trans("Meeting Providers"),
        "redirect": reverse_lazy("meeting-provider-settings"),
        "accessibility": "live_meeting.sidebar.provider_accessibility",
    },
]


def provider_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.is_superuser or request.user.has_perm(
        "pms.manage_meeting_integrations"
    )
