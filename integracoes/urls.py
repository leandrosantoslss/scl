from django.urls import path

from integracoes import views

app_name = "integracoes"

urlpatterns = [
    path("", views.list, name="list"),
    path("novo/", views.create, name="create"),
    path("<int:pk>/", views.detail, name="detail"),
    path("<int:pk>/rotate/", views.rotate, name="rotate"),
    path("<int:pk>/revoke/", views.revoke, name="revoke"),
]
