from django.urls import path

from chhabi_api.api_views.mobile.views import (
    BootstrapAPIView,
    DashboardAPIView,
    MobileRecordDetailAPIView,
    MobileRecordsAPIView,
    MobileModulesAPIView,
    SecureAttendanceAPIView,
    RecruitmentAPIView,
)

urlpatterns = [
    path("bootstrap/", BootstrapAPIView.as_view(), name="mobile-bootstrap"),
    path("dashboard/", DashboardAPIView.as_view(), name="mobile-dashboard"),
    path("modules/", MobileModulesAPIView.as_view(), name="mobile-modules"),
    path("secure-attendance/", SecureAttendanceAPIView.as_view(), name="mobile-secure-attendance"),
    path("recruitment/", RecruitmentAPIView.as_view(), name="mobile-recruitment"),
    path("records/<slug:key>/", MobileRecordsAPIView.as_view(), name="mobile-records"),
    path("records/<slug:key>/<int:pk>/", MobileRecordDetailAPIView.as_view(), name="mobile-record-detail"),
]
