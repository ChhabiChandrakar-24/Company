from django.urls import include, path

urlpatterns = [
    path("collaboration/", include("pms.call_api_urls")),
    path("auth/", include("chhabi_api.api_urls.auth.urls")),
    path("asset/", include("chhabi_api.api_urls.asset.urls")),
    path("base/", include("chhabi_api.api_urls.base.urls")),
    path("employee/", include("chhabi_api.api_urls.employee.urls")),
    path("notifications/", include("chhabi_api.api_urls.notifications.urls")),
    path("payroll/", include("chhabi_api.api_urls.payroll.urls")),
    path("attendance/", include("chhabi_api.api_urls.attendance.urls")),
    path("leave/", include("chhabi_api.api_urls.leave.urls")),
    path("mobile/", include("chhabi_api.api_urls.mobile.urls")),
]
