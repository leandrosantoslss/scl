from django.urls import path

from financeiro import views

app_name = "financeiro"

urlpatterns = [
    path("cobrancas/", views.cobranca_list, name="cobranca-list"),
    path("cobrancas/<int:pk>/", views.cobranca_detail, name="cobranca-detail"),
    path("cobrancas/<int:pk>/pagamento/", views.pagamento_registrar, name="pagamento-registrar"),
    path(
        "cobrancas/<int:cobranca_pk>/estornar/<int:pk>/",
        views.pagamento_estornar,
        name="pagamento-estornar",
    ),
    path("cobrancas/<int:pk>/cancelar/", views.cobranca_cancelar, name="cobranca-cancelar"),
    path("configuracao/", views.configuracao_editar, name="configuracao-editar"),
    path("pagamentos/", views.pagamento_list, name="pagamento-list"),
    path("cobrancas/<int:cobranca_pk>/emissoes/nova/", views.emissao_criar, name="emissao-criar"),
    path("emissoes/<int:pk>/", views.emissao_detalhar, name="emissao-detalhar"),
    path("emissoes/<int:pk>/cancelar/", views.emissao_cancelar, name="emissao-cancelar"),
    path("gateways/", views.gateway_list, name="gateway-list"),
    path("gateways/nova/", views.gateway_create, name="gateway-create"),
    path("gateways/<int:pk>/", views.gateway_detail, name="gateway-detail"),
    path("gateways/<int:pk>/editar/", views.gateway_editar, name="gateway-editar"),
    path("gateways/<int:pk>/toggle/", views.gateway_ativar_desativar, name="gateway-toggle"),
]
