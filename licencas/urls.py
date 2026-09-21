from django.urls import path

from licencas.views import assinaturas, clientes, sistemas

app_name = "licencas"

urlpatterns = [
    path("clientes/", clientes.cliente_list, name="cliente-list"),
    path("clientes/novo/", clientes.cliente_create, name="cliente-create"),
    path("clientes/<int:pk>/", clientes.cliente_detail, name="cliente-detail"),
    path("clientes/<int:pk>/editar/", clientes.cliente_update, name="cliente-update"),
    path("clientes/<int:pk>/bloquear/", clientes.cliente_bloquear, name="cliente-bloquear"),
    path(
        "clientes/<int:pk>/desbloquear/",
        clientes.cliente_desbloquear,
        name="cliente-desbloquear",
    ),
    path("sistemas/", sistemas.sistema_list, name="sistema-list"),
    path("sistemas/novo/", sistemas.sistema_create, name="sistema-create"),
    path("sistemas/<int:pk>/", sistemas.sistema_detail, name="sistema-detail"),
    path("sistemas/<int:pk>/editar/", sistemas.sistema_update, name="sistema-update"),
    path(
        "assinaturas/",
        assinaturas.assinatura_list,
        name="assinatura-list",
    ),
    path("assinaturas/nova/", assinaturas.assinatura_create, name="assinatura-create"),
    path("assinaturas/<int:pk>/", assinaturas.assinatura_detail, name="assinatura-detail"),
    path(
        "assinaturas/<int:pk>/editar/",
        assinaturas.assinatura_update,
        name="assinatura-update",
    ),
    path("assinaturas/<int:pk>/ativar/", assinaturas.assinatura_ativar, name="assinatura-ativar"),
    path(
        "assinaturas/<int:pk>/bloquear/",
        assinaturas.assinatura_bloquear,
        name="assinatura-bloquear",
    ),
    path(
        "assinaturas/<int:pk>/desbloquear/",
        assinaturas.assinatura_desbloquear,
        name="assinatura-desbloquear",
    ),
    path(
        "assinaturas/<int:pk>/desativar/",
        assinaturas.assinatura_desativar,
        name="assinatura-desativar",
    ),
]
