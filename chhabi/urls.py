"""chhabi URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path

import notifications.urls

from . import settings


def health_check(request):
    return JsonResponse({"status": "ok"}, status=200)


urlpatterns = [
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("website.urls")),
    # Website CMS uses a website-prefixed route instead of exposing /admin/.
    path("website/manage/", include("website.admin_urls")),
    path("", include("base.urls")),
    path("", include("chhabi_automations.urls")),
    path("", include("chhabi_views.urls")),
    path("employee/", include("employee.urls")),
    path("report/", include("report.urls")),
    path("chhabi-widget/", include("chhabi_widgets.urls")),
    re_path(
        "^inbox/notifications/", include(notifications.urls, namespace="notifications")
    ),
    path("pms/", include("pms.urls")),
    path("crm/", include("crm.urls")),
    path("billing/", include("payments.urls")),
    path("i18n/", include("django.conf.urls.i18n")),
    path("health/", health_check),
    path("quotations/", include("quotations.urls")),
    path("ai-search/", include("ai_search.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
