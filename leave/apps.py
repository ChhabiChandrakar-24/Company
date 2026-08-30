from django.apps import AppConfig, apps


class LeaveConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "leave"

    def ready(self):
        from django.urls import include, path

        from chhabi.chhabi_settings import APPS
        from chhabi.urls import urlpatterns
        from leave import signals
        from leave.scheduler import start_scheduler

        APPS.append("leave")
        urlpatterns.append(
            path("leave/", include("leave.urls")),
        )
        start_scheduler()
        super().ready()
