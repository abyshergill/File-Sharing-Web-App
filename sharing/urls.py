from django.urls import path

from . import views

app_name = "sharing"

urlpatterns = [
    path("", views.home, name="home"),
    path("upload/", views.upload, name="upload"),
    path("upload/done/", views.upload_done, name="upload_done"),
    path("find/", views.find_file, name="find"),
    path("f/<str:code>/", views.file_detail, name="file_detail"),
    path("f/<str:code>/download/", views.download, name="download"),
    path("my-files/", views.my_files, name="my_files"),
    path("files/<int:pk>/delete/", views.delete_file, name="delete_file"),
]
