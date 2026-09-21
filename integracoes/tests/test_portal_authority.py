import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from integracoes.models import Recurso
from integracoes.services.portal_authority import rejeitar_campos_protegidos
from licencas.models import Cliente
from licencas.tests.helpers import cliente_kwargs, gerar_cpf
from portal.roles import CADASTRO


@pytest.fixture
def cadastro(client):
    group, _ = Group.objects.get_or_create(name=CADASTRO)
    user = get_user_model().objects.create_user("cad", password="secret")
    user.groups.add(group)
    client.force_login(user)
    return client


@pytest.mark.django_db
def test_service_rejeita_campo_protegido(cliente_payload):
    from integracoes.models import IntegracaoLegado, PoliticaIntegracao
    from oauth2_provider.models import Application

    application = Application.objects.create(
        name="Legado", client_type=Application.CLIENT_CONFIDENTIAL,
        authorization_grant_type=Application.GRANT_CLIENT_CREDENTIALS,
    )
    from integracoes.models import IntegracaoLegado as _I

    integracao = _I.objects.create(nome="Legado Master", application=application)
    from integracoes.services.policies import salvar_politica

    usuario = get_user_model().objects.create_user("adm", password="s")
    salvar_politica(
        integration=integracao,
        resource=Recurso.CLIENTE,
        modo="legacy_master",
        writable_fields=["cnpjcpf"],
        usuario=usuario,
        motivo="autoridade legada",
    )

    with pytest.raises(Exception):
        rejeitar_campos_protegidos(Cliente, {"cnpjcpf"})


@pytest.mark.django_db
def test_portal_update_rejeita_post_forjado(cadastro, cliente_payload, integration, policy_factory):
    cliente = Cliente.objects.create(**cliente_payload)
    salvar_politica_legadeira(integration)

    payload = dict(cliente_kwargs("Manipula Nome", "12.345.678/0001-95"))
    # segundo cliente tem documento único — evita colisão com o primeiro

    response = cadastro.post(reverse("licencas:cliente-update", args=[cliente.pk]), data=_payload_completo(payload))
    assert response.status_code in {200, 400}
    cliente.refresh_from_db()
    assert cliente.nome == cliente_payload["nome"]


def salvar_politica_legadeira(integration):
    from integracoes.services.policies import salvar_politica as _sp
    from django.contrib.auth import get_user_model

    usuario = get_user_model().objects.create_user("adm2", password="s")
    _sp(
        integration=integration,
        resource=Recurso.CLIENTE,
        modo="legacy_master",
        writable_fields=["nome"],
        usuario=usuario,
        motivo="m",
    )


def _payload_completo(payload, **extra):
    base = {
        "nome": payload["nome"],
        "cnpjcpf": payload["cnpjcpf"],
        "email": payload["email"],
        "telefone": payload["telefone"],
        "ativo": payload.get("ativo", True),
        "cep": payload["cep"],
        "endereco": payload["endereco"],
        "endnumero": payload["endnumero"],
        "endbairro": payload["endbairro"],
        "endcomplemento": payload["endcomplemento"],
        "endUF": payload["endUF"],
        "endcidade": payload["endcidade"],
        "endcodpais": payload["endcodpais"],
        "endpais": payload["endpais"],
    }
    base.update(extra)
    return base
