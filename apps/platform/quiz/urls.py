"""URLs for the student flow and the instructor live view."""

from django.urls import path

from . import views

app_name = "quiz"

urlpatterns = [
    path("", views.join, name="join"),
    path("q/<int:quiz_id>/identify/", views.identify, name="identify"),
    path("q/<int:quiz_id>/consent/", views.consent, name="consent"),
    path("q/<int:quiz_id>/item/<int:position>/", views.question, name="question"),
    path("q/<int:quiz_id>/usage/", views.usage_mode, name="usage_mode"),
    path("q/<int:quiz_id>/done/", views.done, name="done"),
    path("instructor/q/<int:quiz_id>/live/", views.live, name="live"),
    path("instructor/q/<int:quiz_id>/live/fragment/", views.live_fragment, name="live_fragment"),
    path("instructor/q/<int:quiz_id>/reveal/", views.toggle_reveal, name="toggle_reveal"),
    path("instructor/q/<int:quiz_id>/toggle-open/", views.toggle_open, name="toggle_open"),
    path("instructor/q/<int:quiz_id>/export.csv", views.export, name="export"),
    path("instructor/export.csv", views.export_all, name="export_all"),
]
