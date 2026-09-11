"""URLs for the autograder ingest API."""

from django.urls import path

from . import views

app_name = "autograder"

urlpatterns = [
    path("results/", views.ingest_result, name="ingest_result"),
]
