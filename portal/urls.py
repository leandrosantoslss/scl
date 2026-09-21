from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import RedirectView

from portal import views

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="portal:home", permanent=False)),
    path("login/", views.RememberMeLoginView.as_view(), name="login"),
    path("logout/", views.LogoutPOSTView.as_view(), name="logout"),
    path("password-reset/", views.PasswordResetView.as_view(), name="password_reset"),
    path(
        "password-reset/concluido/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "password-reset/confirmar/<uidb64>/<token>/",
        views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "password-reset/completo/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]
