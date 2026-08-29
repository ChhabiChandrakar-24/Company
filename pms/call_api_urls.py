from rest_framework.routers import DefaultRouter

from .call_api import MeetingViewSet

router = DefaultRouter()
router.register("meetings", MeetingViewSet, basename="meeting-api")
urlpatterns = router.urls
