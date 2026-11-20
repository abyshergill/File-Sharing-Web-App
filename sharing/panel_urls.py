from django.urls import path

from . import panel_views

app_name = "panel"

urlpatterns = [
    path("", panel_views.dashboard, name="dashboard"),
    path("files/", panel_views.files, name="files"),
    path("logs/", panel_views.logs, name="logs"),
    path("settings/", panel_views.site_settings, name="settings"),
    path("cleanup/", panel_views.cleanup, name="cleanup"),
]
