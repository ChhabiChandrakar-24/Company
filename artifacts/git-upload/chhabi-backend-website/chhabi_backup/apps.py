from django.apps import AppConfig


class BackupConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "chhabi_backup"

    def ready(self):
        from django.urls import include, path

        from chhabi.urls import urlpatterns

        urlpatterns.append(
            path("backup/", include("chhabi_backup.urls")),
        )
        super().ready()
