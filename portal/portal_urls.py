from django.urls import path

from portal import views
from portal.views_audit import audit_detail, audit_list

app_name = "portal"

urlpatterns = [
    path("", views.home, name="home"),
    path("auditoria/", audit_list, name="audit_list"),
    path("auditoria/<uuid:public_id>/", audit_detail, name="audit_detail"),
]
