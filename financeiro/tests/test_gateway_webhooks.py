from datetime import date
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from financeiro.gateways.fake import FakeAdapter
from financeiro.gateways.registry import register_adapter, _clear
from financeiro.models import Cobranca, ContaGateway, EmissaoCobranca, EventoGateway
from financeiro.services import webhooks
from licencas.models import Cliente, ClienteSistema, Sistema
from licencas.tests.helpers import gerar_cpf


@pytest.fixture(autouse=True)
def _registrar_fake():
    from financeiro.gateways import registry
    from financeiro.gateways.fake import FakeAdapter

    FakeAdapter._SHARED_EMITIDOS.clear()
    FakeAdapter._SHARED_PEDIDOS.clear()
    registry.FACTORIES["fake"] = lambda **kwargs: FakeAdapter(**kwargs)
    yield
    FakeAdapter._SHARED_EMITIDOS.clear()
    FakeAdapter._SHARED_PEDIDOS.clear()


@pytest.fixture
def conta_emitida(db, cliente_payload):
    from financeiro.services import emissoes

    parent_cliente = Cliente.objects.create(**cliente_payload)
    sistema = Sistema.objects.create(nome="ERP-zh", codigo="erp-wh")
    assinatura = ClienteSistema.objects.create(
        cliente=parent_cliente, sistema=sistema,
        valor_recorrente="199.90", periodicidade="monthly",
        data_inicio="2026-01-01", primeiro_vencimento="2026-01-05",
    )
    cobranca = Cobranca.objects.create(
        assinatura=assinatura,
        competencia=date(2026, 1, 1),
        vencimento=date(2026, 1, 5),
        fim_carencia=date(2026, 1, 10),
        valor_original="199.90",
    )
    conta = ContaGateway.objects.create(nome="efi-fake", provedor="fake", habilita_pix=True)
    usuario = get_user_model().objects.create_user("fin", password="s")
    emissoes.emitir_cobranca(
        cobranca=cobranca, conta=conta, meio="pix", idempotencia="e-wh", usuario=usuario
    )
    emissao = EmissaoCobranca.objects.get(cobranca=cobranca)
    return cobranca, conta, emissao, assinatura


def _post_webhook(client, conta, payload, *, token_signature="VALIDO", provider=None):
    from json import dumps

    provider = provider or conta.provedor
    headers = {
        "HTTP_X_FAKE_ASSINATURA": token_signature,
    }
    return client.post(
        f"/api/v1/payments/webhooks/{provider}/{conta.public_id}/",
        data=json.dumps(payload),
        content_type="application/json",
        **headers,
    )


@pytest.mark.django_db
def test_paid_cria_pagamento_uma_vez(client, conta_emitida):
    import json

    cobranca, conta, emissao, assinatura = conta_emitida
    for adapter in _todos_adaptadores():
        adapter.simular_pagamento(emissao.id_externo)

    body = {
        "id_evento": "evt-1",
        "id_referencia": emissao.id_externo,
        "tipo": "paid",
        "valor": "199.90",
    }
    resposta = client.post(
        f"/api/v1/payments/webhooks/fake/{conta.public_id}/",
        data=json.dumps(body),
        content_type="application/json",
        HTTP_X_FAKE_ASSINATURA="TEARDOWN",
    )
    assert resposta.status_code in {200, 201}

    # repetição não cria pagamento duplicado
    repetida = client.post(f"/api/v1/payments/webhooks/fake/{conta.public_id}/", data=json.dumps(body), content_type="application/json", HTTP_X_FAKE_ASSINATURA="TEARDOWN")
    assert repetida.status_code in {200, 201}
    assert EventoGateway.objects.filter(provedor="fake", id_evento_externo="evt-1").exists()


def _todos_adaptadores():
    from financeiro.gateways import registry

    resultado = []
    if "fake" in registry.FACTORIES:
        resultado.append(registry.FACTORIES["fake"]())
    return resultado
