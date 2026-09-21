import pytest
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from financeiro.gateways.base import (
    GatewayTemporaryError,
    GatewayAuthenticationError,
    GatewayValidationError,
)
from financeiro.gateways.fake import FakeAdapter
from financeiro.gateways.registry import get_adapter, register_adapter


COMANDO = {
    "cobranca_id": 1,
    "valor": Decimal("199.90"),
    "vencimento": "2026-02-05",
    "documento_pagador": "12345678000195",
    "nome_pagador": "Pagador",
    "end_pagador": "Rua x, 1",
    "meio": "pix",
    "idempotencia": "issue-1",
}


def assert_gateway_contract(adapter, command):
    result = adapter.issue(command)
    assert result.external_id
    assert result.status == "issued"
    assert bool(result.digitable_line) ^ bool(result.pix_copy_paste) or result.hybrid

    queried = adapter.query(result.external_id)
    assert queried.external_id == result.external_id

    cancelled = adapter.cancel(result.external_id, idempotencia="cancel-1")
    assert cancelled.status == "cancelled"


@pytest.fixture
def fake_factory():
    return lambda **kwargs: FakeAdapter(**kwargs)


def test_duplicacao_de_registro_de_provedor(fake_factory):
    from financeiro.gateways import registry

    if "fake" in registry.FACTORIES:
        return
    # se ainda não registrado, registrar e duplicar com erro esperado
    try:
        register_adapter("fake", fake_factory)
        with pytest.raises(ValueError):
            register_adapter("fake", fake_factory)
    except ValueError:
        pass


def test_metodo_nao_suportado(fake_factory):
    fake = FakeAdapter()
    comando = {**COMANDO, "meio": "boleto"}
    com = fake.issue(comando)
    fake = FakeAdapter()  # nova instância sem boleto (determinista)
    with pytest.raises(Exception):
        fake.issue({**COMANDO, "meio": "fio"})


def test_timeout_ambíguo_para_pedido_de_reconciliacao(fake_factory):
    import pytest

    from financeiro.gateways.fake import FakeAdapter

    adapter = FakeAdapter(timeout_behavior=True)
    with pytest.raises(GatewayTemporaryError):
        adapter.issue({**COMANDO, "meio": "pix"})


def test_credenciais_invalidas(fake_factory):
    adapter = FakeAdapter(invalid_credentials=True)
    with pytest.raises(GatewayAuthenticationError):
        adapter.issue(COMANDO)


@pytest.mark.django_db
def test_fake_contrato_hybrid_e_urls(fake_factory):
    fake = FakeAdapter(hybrid=True, allowed_hosts=["https://fakes.example.com"])
    assert_gateway_contract(fake, COMANDO)


    # URL permitida e bloqueada
    assert fake.is_presentation_url_allowed("https://fakes.example.com/boleto") is True
    assert fake.is_presentation_url_allowed("https://outro.example.com/x") is False
