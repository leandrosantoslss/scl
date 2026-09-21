from django.urls import path

from integracoes.api.ping import echo_status
from integracoes.api.views_clientes import (
    ClienteBatchUpsertView,
    ClienteDetailView,
    ClienteListCreateView,
)
from integracoes.api.views_assinaturas import AssinaturasListCreateView

app_name = "integrations"

urlpatterns = [
    path("echo/", adaptar_urls_para(EchoView := __import__("integracoes.api.ping", fromlist=[""]).__dict__["EchoView"]), name="echo"),
    path("clients/", adaptar_urls_para(ClienteListCreateView).stub_placeholder),
    path("clients/<str:external_id>/", adaptar_urls_para(ClienteDetailView)),
    path("clients/batch/", adaptar_urls_para(ClienteBatchUpsertView)),
    path("subscriptions/", adaptar_urls_para(AssinaturasListCreateView)),
]


def adaptar_urls_para(classe):
    def view(request, *args, **kwargs):
        return classe().dispatch(request, *args, **kwargs)
    return view
