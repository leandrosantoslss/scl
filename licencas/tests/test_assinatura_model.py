import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from licencas.models import ClienteSistema


def test_subscription_rejects_due_day_above_28(assinatura):
    assinatura.dia_vencimento = 29
    with pytest.raises(ValidationError):
        assinatura.full_clean()


def test_subscription_rejects_grace_and_day_below_1(assinatura):
    assinatura.dia_vencimento = 0
    with pytest.raises(ValidationError):
        assinatura.full_clean()
    assinatura.dia_vencimento = 5
    assinatura.dias_carencia = -1
    assinatura.dias_carencia = -1
    with pytest.raises(Exception):
        assinatura.full_clean()


def test_subscription_rejects_end_before_start(assinatura):
    assinatura.data_fim = assinatura.data_inicio.replace(year=assinatura.data_inicio.year - 1)
    with pytest.raises(ValidationError):
        assinatura.full_clean()


def test_subscription_block_requires_reason(assinatura):
    assinatura.bloqueado = True
    with pytest.raises(ValidationError):
        assinatura.full_clean()


@pytest.mark.django_db
def test_client_system_pair_is_unique(assinatura):
    with pytest.raises(IntegrityError):
        ClienteSistema.objects.create(
            cliente=assinatura.cliente,
            sistema=assinatura.sistema,
            valor_recorrente="1.00",
            periodicidade="monthly",
            data_inicio=assinatura.data_inicio,
            primeiro_vencimento=assinatura.primeiro_vencimento,
        )


@pytest.mark.django_db
def test_active_subscription_with_zero_amount_is_rejected(db, cliente_payload):
    from licencas.models import Cliente, Sistema

    cliente = Cliente.objects.create(**cliente_payload, cnpjcpf="12345678000195")
    sistema = Sistema.objects.create(nome="ERP", codigo="erp")
    with pytest.raises(Exception):
        ClienteSistema.objects.create(
            cliente=cliente,
            sistema=sistema,
            valor_recorrente="0.00",
            periodicidade="monthly",
            data_inicio="2026-01-01",
            primeiro_vencimento="2026-01-05",
        )


@pytest.mark.django_db
def test_activate_with_zero_amount_is_rejected(db, cliente_payload):
    from portal import audit  # noqa: F401  (garante que auditoria segue disponível)

    from licencas.services import assinaturas
    from licencas.models import Cliente, ClienteSistema, Sistema
    from django.contrib.auth import get_user_model

    cliente = Cliente.objects.create(**cliente_payload, cnpjcpf="12345678000195")
    sistema = Sistema.objects.create(nome="ERP", codigo="erp-2")
    desativada = ClienteSistema.objects.create(
        cliente=cliente,
        sistema=sistema,
        valor_recorrente=0,
        periodicidade="monthly",
        data_inicio="2026-01-01",
        primeiro_vencimento="2026-01-05",
        ativo=False,
    )
    usuario = get_user_model().objects.create_user("op", password="secret")
    with pytest.raises(Exception):
        assinaturas.ativar_assinatura(desativada, usuario=usuario)


@pytest.mark.django_db
def test_activate_succeeds_after_positive_value(db, cliente_payload):
    from licencas.services import assinaturas
    from licencas.models import Cliente, ClienteSistema, Sistema
    from django.contrib.auth import get_user_model

    cliente = Cliente.objects.create(**cliente_payload, cnpjcpf="12345678000195")
    sistema = Sistema.objects.create(nome="ERP", codigo="erp-3")
    desativada = ClienteSistema.objects.create(
        cliente=cliente,
        sistema=sistema,
        valor_recorrente=0,
        periodicidade="monthly",
        data_inicio="2026-01-01",
        primeiro_vencimento="2026-01-05",
        ativo=False,
    )
    usuario = get_user_model().objects.create_user("op", password="secret")

    assinaturas.atualizar_comercial(desativada, valor_recorrente="199.90", usuario=usuario)
    ativa = assinaturas.ativar_assinatura(desativada, usuario=usuario)
    assert ativa.ativo is True
