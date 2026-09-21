from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from financeiro.gateways.fake import FakeAdapter
from financeiro.gateways.registry import register_adapter, _clear
from financeiro.models import Cobranca, ContaGateway, EmissaoCobranca, Pagamento
from financeiro.services import emissoes
from licencas.models import Cliente, ClienteSistema, Sistema
from licencas.tests.helpers import cliente_kwargs, data_comercial, gerar_cpf
from portal.models import EventoAuditoria


@pytest.fixture(autouse=True)
def _registry_fake():
    from financeiro.gateways import registry
    from financeiro.gateways.fake import FakeAdapter

    FakeAdapter._SHARED_EMITIDOS.clear()
    FakeAdapter._SHARED_PEDIDOS.clear()
    if "fake" not in registry.FACTORIES:
        registry.register_adapter("fake", lambda **kwargs: FakeAdapter(**kwargs))
    yield
    FakeAdapter._SHARED_EMITIDOS.clear()
    FakeAdapter._SHARED_PEDIDOS.clear()


@pytest.fixture
def conta_fake(db):
    return ContaGateway.objects.create(nome="Fake Pix", provedor="fake", habilita_pix=True)


@pytest.fixture
def cobranca_legado(db, cliente_payload):
    cliente = Cliente.objects.create(**cliente_payload)
    sistema = Sistema.objects.create(nome="ERP", codigo="erp-emit")
    assinatura = ClienteSistema.objects.create(
        cliente=cliente, sistema=sistema,
        valor_recorrente="10.00", periodicidade="monthly", data_inicio="2026-01-01", primeiro_vencimento="2026-01-05",
    )
    return Cobranca.objects.create(
        assinatura=assinatura,
        competencia=date(2026, 1, 1),
        vencimento=date(2026, 1, 5),
        fim_carencia=date(2026, 1, 10),
        valor_original="199.90",
    )


@pytest.fixture
def usuario(db):
    return get_user_model().objects.create_user("fin", password="s")


def _comando(cobranca):
    return {
        "cobranca_id": cobranca.pk,
        "valor": cobranca.valor_original,
        "vencimento": cobranca.vencimento.isoformat(),
        "documento_pagador": str(cobranca.assinatura.cliente.cnpjcpf),
        "nome_pagador": cobranca.assinatura.cliente.nome,
        "end_pagador": f"{cobranca.assinatura.cliente.endereco} n. {cobranca.assinatura.cliente.endnumero}",
        "meio": "pix",
        "idempotencia": "e-1",
    }


@pytest.mark.django_db
def test_emitir_e_cancelar(conta_fake, cobranca_legado, usuario):
    emissao = emissoes.emitir_cobranca(
        cobranca=cobranca_legado,
        conta=conta_fake,
        meio="pix",
        idempotencia="e-1",
        usuario=usuario,
    )
    emissao.refresh_from_db()
    assert emissao.status == EmissaoCobranca.Status.ISSUED
    assert emissao.id_externo

    # 5. Apenas uma emissão ativa por cobrança
    with pytest.raises(Exception):
        emissoes.emitir_cobranca(
            cobranca=cobranca_legado, conta=conta_fake, meio="pix", idempotencia="e-2", usuario=usuario
        )

    cancelada = emissoes.cancelar_emissao(emissao=emissao, idempotencia="c-1", usuario=usuario)
    assert cancelada.status == EmissaoCobranca.Status.CANCELLED
    assert EventoAuditoria.objects.filter(acao="emissao.cobranca.emitida").exists()


@pytest.mark.django_db
def test_conta_inativa_ou_meio_desabilitado(conta_fake, cobranca_legado, usuario):
    from financeiro.gateways.fake import FakeAdapter  # noqa: F401

    conta_fake.habilita_pix = True
    conta_fake.save()

    # meo desabilitado
    conta_sem_boleto = ContaGateway.objects.create(
        nome="Sem Boleto", provedor="fake", habilita_boleto=False, habilita_pix=True
    )
    with pytest.raises(Exception):
        emissoes.emitir_cobranca(
            cobranca=cobranca_legado,
            conta=conta_sem_boleto,
            meio="boleto",
            idempotencia="e-m-b",
            usuario=usuario,
        )

    # conta inativa
    conta_fake.ativo = False
    conta_fake.save()
    with pytest.raises(Exception):
        emissoes.emitir_cobranca(
            cobranca=cobranca_legado, conta=conta_fake, meio="pix", idempotencia="e-2", usuario=usuario
        )


@pytest.mark.django_db
def test_cobranca_cancelada_ou_paga_nao_aceita_emissao(conta_fake, cobranca_legado, usuario):
    cobranca_legado.status = Cobranca.Status.CANCELADA
    cobranca_legado.save()
    with pytest.raises(Exception):
        emissoes.emitir_cobranca(
            cobranca=cobranca_legado, conta=conta_fake, meio="pix", idempotencia="e-3", usuario=usuario
        )


@pytest.mark.django_db
def test_timeout_ambiguo_permanece_pendente(cobranca_legado, usuario, conta_fake):
    from financeiro.gateways import registry

    registry.FACTORIES["fake"] = lambda **kwargs: FakeAdapter(timeout_behavior=True)

    emissoes.emitir_cobranca(
        cobranca=cobranca_legado,
        conta=conta_fake,
        meio="pix",
        idempotencia="t-1",
        usuario=usuario,
    )
    emissao = EmissaoCobranca.objects.get(chave_idempotencia="t-1")
    assert emissao.status == EmissaoCobranca.Status.PENDING_UNKNOWN
