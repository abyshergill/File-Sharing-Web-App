from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", include("sharing.urls")),
    path("accounts/", include("accounts.urls")),
    path("panel/", include("sharing.panel_urls")),
    path("django-admin/", admin.site.urls),
]
