from django.utils.translation import gettext_lazy as trans


MENU = trans("Live Meetings")
IMG_SRC = "images/ui/pms.svg"

SUBMENUS = [
    {
        "menu": trans("All Meetings"),
        "redirect": "/pms/view-meetings/",
    },
    {
        "menu": trans("Create Meeting"),
        "redirect": "/pms/create-meeting-shortcut/",
    },
    {
        "menu": trans("Subscription & Plans"),
        "redirect": "/pms/subscription/plans/",
    },
    {
        "menu": trans("Developer API & SDK"),
        "redirect": "/pms/developer/portal/",
    },
    {
        "menu": trans("Billing History"),
        "redirect": "/pms/subscription/transactions/",
    },
    {
        "menu": trans("Payment Gateways"),
        "redirect": "/pms/subscription/admin/gateways/",
        "accessibility": "live_meeting.sidebar.provider_accessibility",
    },
    {
        "menu": trans("Meeting Providers"),
        "redirect": "/pms/meeting-provider-settings/",
        "accessibility": "live_meeting.sidebar.provider_accessibility",
    },
]


def provider_accessibility(request, submenu, user_perms, *args, **kwargs):
    return request.user.is_superuser or request.user.has_perm(
        "pms.manage_meeting_integrations"
    )
