from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from apps.gardens.permissions import render_denied


def custom_403(request, exception=None):
    """全局 403：统一渲染中文说明页。"""
    return render_denied(request)


handler403 = custom_403

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("apps.gardens.urls")),
]
