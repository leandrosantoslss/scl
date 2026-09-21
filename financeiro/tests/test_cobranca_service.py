from datetime import date

import pytest
from django.core.exceptions import ValidationError

from financeiro.models import Cobranca, ConfiguracaoFinanceira
from financeiro.services.cobrancas import gerar_cobrancas_assinatura, meses_por_periodicidade


def test_meses_por_periodicidade():
    assert meses_por_periodicidade("monthly") == 1
    assert meses_por_periodicidade("quarterly") == 3
    assert meses_por_periodicidade("semiannual") == 6
    assert meses_por_periodicidade("annual") == 12


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("periodicidade", "expected"),
    [
        ("monthly", ["2026-01-05", "2026-02-05", "2026-03-05"]),
        ("quarterly", ["2026-01-05", "2026-04-05"]),
        ("semiannual", ["2026-01-05", "2026-07-05"]),
        ("annual", ["2026-01-05", "2027-01-05"]),
    ],
)
def test_generates_expected_calendar_cycles(assinatura_factory, periodicidade, expected):
    assinatura = assinatura_factory(
        periodicidade=periodicidade,
        primeiro_vencimento=date(2026, 1, 5),
        dia_vencimento=5,
    )
    charges = gerar_cobrancas_assinatura(assinatura, ate=date.fromisoformat(expected[-1]))
    assert [charge.vencimento.isoformat() for charge in charges] == expected


@pytest.mark.django_db
def test_fixed_term_stops_at_data_fim(assinatura_factory):
    from datetime import date

    assinatura = assinatura_factory(
        periodicidade="monthly",
        primeiro_vencimento=date(2026, 1, 5),
        dia_vencimento=5,
        data_fim=date(2026, 2, 20),
    )
    charges = gerar_cobrancas_assinatura(assinatura, ate=date(2026, 12, 31))
    vencimentos = [charge.vencimento.isoformat() for charge in charges]
    assert "2026-01-05" in vencimentos
    assert "2026-02-05" in vencimentos
    assert "2026-03-05" not in vencimentos


@pytest.mark.django_db
def test_indefinite_term_keeps_upcoming_charge(assinatura_factory):
    from datetime import date

    assinatura = assinatura_factory(
        periodicidade="monthly",
        primeiro_vencimento=date(2026, 6, 5),
        dia_vencimento=5,
    )
    charges = gerar_cobrancas_assinatura(assinatura, ate=date(2026, 6, 30))
    vencimentos = [charge.vencimento.isoformat() for charge in charges]
    assert "2026-06-05" in vencimentos


@pytest.mark.django_db
def test_grace_snapshot_uses_subscription_override(assinatura_factory):
    from datetime import date

    assinatura = assinatura_factory(dia_vencimento=5, dias_carencia=7)
    charges = gerar_cobrancas_assinatura(assinatura, ate=date(2026, 1, 5))
    assert charges[0].fim_carencia == date(2026, 1, 12)


@pytest.mark.django_db
def test_grace_snapshot_uses_global_config_without_override(assinatura_factory):
    from datetime import date

    ConfiguracaoFinanceira.objects.create(dia_vencimento=5, dias_carencia=3)
    assinatura = assinatura_factory(dia_vencimento=5, dias_carencia=None)
    charges = gerar_cobrancas_assinatura(assinatura, ate=date(2026, 1, 5))
    assert charges[0].fim_carencia == date(2026, 1, 8)


@pytest.mark.django_db
def test_inactive_subscription_produces_no_charges(assinatura_factory):
    from datetime import date

    assinatura = assinatura_factory(ativo=False)
    charges = gerar_cobrancas_assinatura(assinatura, ate=date(2026, 12, 31))
    assert list(charges) == []


@pytest.mark.django_db
def test_repeated_calls_do_not_duplicate(assinatura_factory):
    from datetime import date

    assinatura = assinatura_factory(dia_vencimento=5)
    first = gerar_cobrancas_assinatura(assinatura, ate=date(2026, 3, 5))
    second = gerar_cobrancas_assinatura(assinatura, ate=date(2026, 3, 5))
    assert len(first) == 3
    assert list(second) == []
    assert Cobranca.objects.filter(assinatura=assinatura).count() == 3
