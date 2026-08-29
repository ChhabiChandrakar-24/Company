from django.urls import path

from . import manager_views


urlpatterns = [
    path("attendance-evidence/", manager_views.attendance_evidence, name="website-attendance-evidence"),
    path("attendance-evidence/<int:object_id>/selfie/", manager_views.attendance_selfie, name="website-attendance-selfie"),
    path("<str:section>/", manager_views.cms_list, name="website-manage-list"),
    path("<str:section>/add/", manager_views.cms_form, name="website-manage-add"),
    path("<str:section>/<int:object_id>/edit/", manager_views.cms_form, name="website-manage-edit"),
    path("<str:section>/<int:object_id>/delete/", manager_views.cms_delete, name="website-manage-delete"),
]
