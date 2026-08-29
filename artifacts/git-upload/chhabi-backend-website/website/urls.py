from django.urls import path
from . import views

urlpatterns = [
    path("", views.public_page, {"slug": "home"}, name="website-home"),
    path("about/", views.public_page, {"slug": "about"}, name="website-about"),
    path("services/", views.public_page, {"slug": "services"}, name="website-services"),
    path("pricing/", views.public_page, {"slug": "pricing"}, name="website-pricing"),
    path("career/", views.public_page, {"slug": "career"}, name="website-career"),
    path("contact/", views.public_page, {"slug": "contact"}, name="website-contact"),
    path("faq/", views.public_page, {"slug": "faq"}, name="website-faq"),
    path("team/", views.public_page, {"slug": "team"}, name="website-team"),
    path("projects/", views.public_page, {"slug": "projects"}, name="website-projects"),
    path("terms-and-conditions/", views.public_page, {"slug": "terms-and-conditions"}, name="website-terms"),
    path("thank-you/", views.public_page, {"slug": "thank-you"}, name="website-thank-you"),
    path("website/submit/", views.submit, name="website-submit"),
]
