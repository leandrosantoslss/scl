import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from financeiro.models import Cobranca, Pagamento
from financeiro.selectors import obter_posicao_financeira
from financeiro.services.pagamentos import (
    cancelar_cobranca_scl,
    estornar_pagamento,
    registrar_pagamento_manual,
)


@pytest.fixture
def vencida_basica(assinatura_factory):
    from datetime import date

    assinatura = assinatura_factory(dia_vencimento=5)
    cobranca = Cobranca.objects.create(
        assinatura=assinatura,
        competencia=date(2026, 1, 1),
        vencimento=date(2026, 1, 5),
        fim_carencia=date(2026, 1, 10),
        valor_original="100.00",
    )
    return assinatura, cobranca


@pytest.mark.django_db
def test_exact_date_boundaries(vencida_basica):
    from datetime import date

    assinatura, _cobranca = vencida_basica
    assert obter_posicao_financeira(assinatura, hoje=date(2026, 1, 5)).code == "CURRENT"
    assert obter_posicao_financeira(assinatura, hoje=date(2026, 1, 6)).code == "OVERDUE_IN_GRACE"
    assert obter_posicao_financeira(assinatura, hoje=date(2026, 1, 10)).code == "OVERDUE_IN_GRACE"
    assert obter_posicao_financeira(assinatura, hoje=date(2026, 1, 11)).code == "DELINQUENT"


@pytest.mark.django_db
def test_grace_zero_goes_straight_to_delinquent(assinatura_factory):
    from datetime import date

    assinatura = assinatura_factory(dias_carencia=0)
    Cobranca.objects.create(
        assinatura=assinatura,
        competencia=date(2026, 1, 1),
        vencimento=date(2026, 1, 5),
        fim_carencia=date(2026, 1, 5),
        valor_original="50.00",
    )
    posicao = obter_posicao_financeira(assinatura, hoje=date(2026, 1, 6))
    assert posicao.code == "DELINQUENT"
    assert posicao.allowed is False


@pytest.mark.django_db
def test_oldest_of_multiple_balances(vencida_basica):
    from datetime import date

    assinatura, cobranca = vencida_basica
    Cobranca.objects.create(
        assinatura=assinatura,
        competencia=date(2026, 2, 1),
        vencimento=date(2026, 2, 5),
        fim_carencia=date(2026, 2, 10),
        valor_original="80.00",
    )
    posicao = obter_posicao_financeira(assinatura, hoje=date(2026, 1, 7))
    assert posicao.oldest_due_date == date(2026, 1, 5)
    assert posicao.grace_ends_on == date(2026, 1, 10)
    assert posicao.outstanding_amount == 180.00


@pytest.mark.django_db
def test_partial_and_full_payment_vencida_basica(vencida_basica):
    from datetime import date
    from decimal import Decimal

    assinatura, cobranca = vencida_basica
    usuario = get_user_model().objects.create_user("fin", password="s")

    primeiro = registrar_pagamento_manual(
        cobranca=cobranca, valor=Decimal("40.00"), pago_em=timezone.now(), forma="dinheiro", usuario=usuario
    )
    posicao = obter_posicao_financeira(assinatura, hoje=date(2026, 1, 7))
    assert posicao.outstanding_amount == 60.00

    registrar_pagamento_manual(
        cobranca=cobranca, valor=Decimal("60.00"), pago_em=timezone.now(), forma="pix", usuario=usuario
    )
    cobranca.refresh_from_db()
    assert cobranca.status == Cobranca.Status.PAGA
    posicao = obter_posicao_financeira(assinatura, hoje=date(2026, 1, 7))
    assert posicao.code == "CURRENT"
    assert primeiro.status == Pagamento.Status.CONFIRMED


@pytest.mark.django_db
def test_reversal_restores_exact_balance(vencida_basica):
    from datetime import date
    from decimal import Decimal

    assinatura, cobranca = vencida_basica
    usuario = get_user_model().objects.create_user("fin", password="s")

    antes = obter_posicao_financeira(assinatura, hoje=date(2026, 1, 7))
    pagamento = registrar_pagamento_manual(
        cobranca=cobranca, valor=Decimal("100.00"), pago_em=timezone.now(), forma="pix", usuario=usuario
    )
    depois_pagamento = obter_posicao_financeira(assinatura, hoje=date(2026, 1, 7))
    assert antes.outstanding_amount - depois_pagamento.outstanding_amount == 100.00

    estornar_pagamento(pagamento=pagamento, motivo="erro de digitação", usuario=usuario)
    depois_estorno = obter_posicao_financeira(assinatura, hoje=date(2026, 1, 7))
    assert depois_estorno.outstanding_amount == antes.outstanding_amount
    pagamento.refresh_from_db()
    assert pagamento.status == Pagamento.Status.REVERSED


@pytest.mark.django_db
def test_reversal_rejects_duplicate_and_requires_reason(vencida_basica):
    from decimal import Decimal

    _assinatura, cobranca = vencida_basica
    usuario = get_user_model().objects.create_user("fin", password="s")
    pagamento = registrar_pagamento_manual(
        cobranca=cobranca, valor=Decimal("10.00"), pago_em=timezone.now(), forma="pix", usuario=usuario
    )

    estornar_pagamento(pagamento=pagamento, motivo="réplica", usuario=usuario)
    with pytest.raises(ValidationError):
        estornar_pagamento(pagamento=pagamento, motivo="segunda vez", usuario=usuario)

    pagamento_novo = registrar_pagamento_manual(
        cobranca=cobranca, valor=Decimal("10.00"), pago_em=timezone.now(), forma="pix", usuario=usuario
    )
    with pytest.raises(ValidationError):
        estornar_pagamento(pagamento=pagamento_novo, motivo="   ", usuario=usuario)


@pytest.mark.django_db
def test_canceled_charge_never_contributes(vencida_basica):
    from datetime import date

    assinatura, cobranca = vencida_basica
    usuario = get_user_model().objects.create_user("fin", password="s")
    cancelar_cobranca_scl(cobranca=cobranca, motivo="não é mais cobrada", usuario=usuario)

    posicao = obter_posicao_financeira(assinatura, hoje=date(2026, 1, 12))
    assert posicao.code == "CURRENT"
    assert posicao.outstanding_amount == 0.00


@pytest.mark.django_db
def test_cancel_rejects_non_scl_or_with_confirmed_payment(vencida_basica):
    from decimal import Decimal

    _assinatura, cobranca = vencida_basica
    usuario = get_user_model().objects.create_user("fin", password="s")

    from unittest.mock import patch

    pagamento = registrar_pagamento_manual(
        cobranca=cobranca, valor=Decimal("10.00"), pago_em=timezone.now(), forma="pix", usuario=usuario
    )
    with pytest.raises(ValidationError):
        cancelar_cobranca_scl(cobranca=cobranca, motivo="tchau", usuario=usuario)

    cobranca.status = Cobranca.Status.ABERTA
    cobranca.save()
    from financeiro.models import Cobranca as C

    legada = C.objects.create(
        assinatura=vencida_basica[0],
        competencia="2026-03-01",
        vencimento="2026-03-05",
        fim_carencia="2026-03-10",
        valor_original="70.00",
        origem="legacy",
    )
    with pytest.raises(ValidationError):
        cancelar_cobranca_scl(cobranca=legada, motivo="não é scl", usuario=usuario)
