from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(redirect_authenticated_user=True), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "password/",
        auth_views.PasswordChangeView.as_view(success_url=reverse_lazy("accounts:password_changed")),
        name="password_change",
    ),
    path("password/done/", auth_views.PasswordChangeDoneView.as_view(), name="password_changed"),
    path("users/", views.user_list, name="user_list"),
    path("users/new/", views.user_create, name="user_create"),
    path("users/<int:pk>/", views.user_edit, name="user_edit"),
    path("users/<int:pk>/password/", views.user_set_password, name="user_set_password"),
    path("users/<int:pk>/delete/", views.user_delete, name="user_delete"),
]
