from django.urls import path

from integracoes.api.ping import adaptar_para_urls, echo_status
from integracoes.api.views_clientes import (
    ClienteBatchUpsertView,
    ClienteDetailView,
    ClienteListCreateView,
)
from integracoes.api.views_assinaturas import AssinaturasListCreateView
from integracoes.api.views_financeiro import ChargesCreateListView
from integracoes.api.views_pagamentos import (
    ChargesDetalheCancelarView,
    CobrancaCancelarView,
    PagamentoEstornoView,
    PagamentosCreateListView,
)

app_name = "integrations"

urlpatterns = [
    path("echo/", echo_status, name="echo"),
    path("clients/", adaptar_para_urls(ClienteListCreateView)),
    path("clients/batch/", adaptar_para_urls(ClienteBatchUpsertView)),
    path("clients/<str:external_id>/", adaptar_para_urls(ClienteDetailView)),
    path("subscriptions/", adaptar_para_urls(AssinaturasListCreateView)),
    path("charges/", adaptar_para_urls(ChargesCreateListView)),
    path("charges/<str:external_id>/", adaptar_para_urls(ChargesDetalheCancelarView)),
    path("payments/", adaptar_para_urls(PagamentosCreateListView)),
    path("payments/<str:external_id>/reverse/", adaptar_para_urls(PagamentoEstornoView)),
]
