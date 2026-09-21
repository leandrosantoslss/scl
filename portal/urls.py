from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import RedirectView

from portal import views

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="portal:home", permanent=False)),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutPOSTView.as_view(), name="logout"),
]
