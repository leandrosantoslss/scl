from django.contrib.auth import views as auth_views
from django.urls import path

from portal import views

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutPOSTView.as_view(), name="logout"),
]
