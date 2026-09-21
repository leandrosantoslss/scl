import hashlib
from datetime import datetime, timedelta, timezone as dt_timezone

import pytest
from oauth2_provider.models import AccessToken

from integracoes.api.etag import version_for
from integracoes.models import Recurso
from integracoes.services import references
from licencas.models import Cliente
from licencas.tests.helpers import cliente_kwargs, gerar_cpf

TOKEN = "clients-api-token"


@pytest.fixture
def token_db(integration, db):
    AccessToken.objects.create(
        token=TOKEN,
        expires=datetime.now(dt_timezone.utc) + timedelta(minutes=10),
        scope="clients:read clients:write subscriptions:read subscriptions:write payments:write payments:reverse finance:read finance:write",
        application=integration.application,
        user=None,
    )
    return integration


def _auth():
    return {"HTTP_AUTHORIZATION": f"Bearer {TOKEN}"}


URL = "/api/v1/integrations/clients/"

PAYL_BASE = {
    "email": "a@x.com",
    "telefone": "1",
    "cep": "1",
    "endereco": "R",
    "endnumero": "1",
    "endbairro": "B",
    "endcomplemento": "-",
    "endUF": "SP",
    "endcidade": "S",
    "endcodpais": 55,
    "endpais": "Brasil",
}


@pytest.fixture
def policy_shared(policy_factory, integration):
    policy_factory(
        integration=integration,
        recurso=Recurso.CLIENTE,
        modo="shared",
        readable_fields=["*"],
        writable_fields=["nome", "email", "telefone", "ativo"],
    )
    return integration


@pytest.mark.django_db
def test_list_retorna_campos_com_cursor(client, token_db, policy_shared, cliente_payload):
    Cliente.objects.create(**cliente_payload)
    resposta = client.get(URL, **_auth())
    assert resposta.status_code == 200
    primeiro = resposta.json()["items"][0]
    assert {"external_id", "internal_id", "version", "updated_at", "nome"}.issubset(primeiro.keys())


@pytest.mark.django_db
def test_consultar_por_external_id_404(client, token_db, policy_shared):
    resposta = client.get(URL + "c-inexistente/", **_auth())
    assert resposta.status_code == 404


@pytest.mark.django_db
def test_post_cria_e_recria_duplicado(client, token_db, policy_shared, cliente_payload):
    cubo_payload = {
        **cliente_kwargs("Nova", "12.345.678/0001-95", email="novo@x.com"),
        "external_id": "c-1",
    }
    resposta = client.post(
        URL,
        data=cubo_payload,
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY="k1",
        **_auth(),
    )
    assert resposta.status_code == 201

    integration = token_db
    cliente = Cliente.objects.get(cnpjcpf="12345678000195")
    assert cliente.referencias_externas.filter(
        external_id="c-1", integration_id=integration.id
    ).exists()

    # POST repetido com mesma chave vai à sua external_id existente: replay 200
    resposta = client.post(
        URL,
        data=cubo_payload,
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY="k1",
        **_auth(),
    )
    assert resposta.status_code in {200, 201}

    # Mesmo documento com outra external_id viola unique → 409
    resposta = client.post(
        URL,
        data={**cubo_payload, "external_id": "c-2"},
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY="k2",
        **_auth(),
    )
    assert resposta.status_code == 409


@pytest.mark.django_db
def test_patch_shared_exige_etag_e_rejeita_obsoleto(client, token_db, policy_shared, cliente_payload):
    cliente = Cliente.objects.create(**cliente_payload)
    references.obter_ou_criar_referencia(
        Cliente, integration=token_db, external_id="c-up", objeto=cliente
    )
    cliente = Cliente.objects.get(pk=cliente.pk)
    etag_atual = version_for(cliente)

    resposta = client.patch(
        URL + "c-up/",
        data={"nome": "Prime updated"},
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY="p-1",
        **_auth(),
    )
    assert resposta.status_code == 409

    resposta = client.patch(
        URL + "c-up/",
        data={"nome": "Prime updated"},
        content_type="application/json",
        HTTP_IF_MATCH='"obsoleta"',
        HTTP_IDEMPOTENCY_KEY="p-1",
        **_auth(),
    )
    assert resposta.status_code == 409
    assert resposta.json()["code"] == "VERSION_CONFLICT"

    resposta = client.patch(
        URL + "c-up/",
        data={"nome": "Prime updated"},
        content_type="application/json",
        HTTP_IF_MATCH=f'"{etag_atual}"',
        HTTP_IDEMPOTENCY_KEY="p-1",
        **_auth(),
    )
    assert resposta.status_code == 200


@pytest.mark.django_db
def test_scl_master_bloqueia_post(client, token_db, policy_factory, policy_shared, cliente_payload):
    # Sobrepõe a política de client com scl_master.
    integration = token_db
    from integracoes.services.policies import salvar_politica
    from django.contrib.auth import get_user_model

    usuario = get_user_model().objects.create_user("adm", password="s")
    salvar_politica(
        integration=integration,
        resource=Recurso.CLIENTE,
        modo="scl_master",
        readable_fields=["*"],
        usuario=usuario,
        motivo="bloqueio",
    )
    payload = {
        **cliente_kwargs("D", gerar_cpf(115)),
        "external_id": "c-scl",
    }
    resposta = client.post(
        URL,
        data=payload,
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY="k-scl",
        **_auth(),
    )
    assert resposta.status_code == 403


@pytest.mark.django_db
def test_batch_upsert_um_valido_um_invalido(client, token_db, policy_shared):
    payload = {
        "items": [
            {
                "external_id": "c-b1",
                "nome": "Batch Um",
                "cnpjcpf": gerar_cpf(201),
                "email": "a@x.com",
                "telefone": "1",
                "cep": "1",
                "endereco": "R",
                "endnumero": "1",
                "endbairro": "B",
                "endcomplemento": "-",
                "endUF": "SP",
                "endcidade": "S",
                "endcodpais": 55,
                "endpais": "Brasil",
            },
            {"external_id": "c-b2", "nome": "Batch Dois", "cnpjcpf": "11111111111"},
        ]
    }
    resposta = client.post(
        URL + "batch/",
        data=payload,
        content_type="application/json",
        HTTP_IDEMPOTENCY_KEY="b-1",
        **_auth(),
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["aceitos"] == 1
    assert corpo["rejeitados"] == 1
    from licencas.models import Cliente

    assert Cliente.objects.filter(nome="Batch Um").exists()


@pytest.mark.django_db
def test_inactive_permanece_visivel(client, token_db, policy_shared, cliente_payload):
    cliente = Cliente.objects.create(
        **cliente_payload, ativo=False
    )
    references.obter_ou_criar_referencia(
        Cliente, integration=token_db, external_id="c-off", objeto=cliente
    )
    resposta = client.get(URL + "c-off/", **_auth())
    assert resposta.status_code == 200
    assert resposta.json()["ativo"] is False
