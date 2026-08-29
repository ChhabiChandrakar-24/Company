from django.apps import AppConfig


class ChhabiApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "chhabi_api"

    def ready(self):
        from django.urls import include, path

        from chhabi.urls import urlpatterns

        urlpatterns.append(
            path("api/", include("chhabi_api.urls")),
        )
        super().ready()
