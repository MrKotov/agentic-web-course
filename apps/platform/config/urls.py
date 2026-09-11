"""Root URL configuration."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/autograder/", include("autograder.urls")),
    path("", include("quiz.urls")),
]
