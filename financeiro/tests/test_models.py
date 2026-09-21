import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from financeiro.models import Cobranca, ConfiguracaoFinanceira, Pagamento


@pytest.mark.django_db
def test_financial_config_rejects_due_day_29():
    config = ConfiguracaoFinanceira(dia_vencimento=29, dias_carencia=5)
    with pytest.raises(ValidationError):
        config.full_clean()


@pytest.mark.django_db
def test_financial_config_rejects_negative_grace():
    config = ConfiguracaoFinanceira(dia_vencimento=5, dias_carencia=-1)
    with pytest.raises(Exception):
        ConfiguracaoFinanceira.objects.create(dia_vencimento=5, dias_carencia=-1)


@pytest.mark.django_db
def test_financial_config_is_database_singleton():
    ConfiguracaoFinanceira.objects.create()
    with pytest.raises(Exception):
        ConfiguracaoFinanceira.objects.create(dia_vencimento=10)

    second = ConfiguracaoFinanceira()
    second.id = 2
    with pytest.raises(Exception):
        second.save()


@pytest.mark.django_db
def test_charge_cycle_is_unique(assinatura, cobranca_payload):
    Cobranca.objects.create(assinatura=assinatura, **cobranca_payload)
    with pytest.raises(IntegrityError):
        Cobranca.objects.create(assinatura=assinatura, **cobranca_payload)


@pytest.mark.django_db
def test_charge_rejects_non_positive_amount(assinatura):
    payload = dict(
        competencia="2026-01-01",
        vencimento="2026-01-05",
        fim_carencia="2026-01-10",
        valor_original="0.00",
    )
    with pytest.raises(Exception):
        Cobranca.objects.create(assinatura=assinatura, **payload)


@pytest.mark.django_db
def test_charge_rejects_grace_before_due(assinatura, cobranca_payload):
    payload = dict(cobranca_payload)
    payload["fim_carencia"] = "2026-01-04"
    with pytest.raises(Exception):
        Cobranca.objects.create(assinatura=assinatura, **payload)


@pytest.mark.django_db
def test_payment_requires_positive_amount(assinatura, cobranca_payload):
    cobranca = Cobranca.objects.create(assinatura=assinatura, **cobranca_payload)
    usuario = get_user_model().objects.create_user("op", password="s")

    with pytest.raises(Exception):
        Pagamento.objects.create(
            cobranca=cobranca,
            valor=0,
            pago_em="2026-01-05 12:00:00+03:00",
            forma="pix",
            origem="manual",
            status="confirmed",
            usuario=usuario,
        )
