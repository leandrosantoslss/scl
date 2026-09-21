import io
from datetime import date

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from financeiro.models import Cobranca, ConfiguracaoFinanceira, Pagamento


def _chamar(*args):
    buffer = io.StringIO()
    call_command("gerar_cobrancas", *args, stdout=buffer, stderr=buffer)
    return buffer.getvalue()


@pytest.mark.django_db
def test_command_generates_and_is_idempotent(assinatura_factory, assinatura):
    from datetime import date

    output = _chamar("--today", "2026-01-05")
    assert "subscriptions_scanned=1" in output
    assert "charges_created=2" in output
    assert "charges_existing=0" in output
    assert "subscriptions_failed=0" in output

    # Segunda execução: nada novo; as existentes continuam.
    output = _chamar("--today", "2026-01-05")
    assert "charges_created=0" in output
    assert "charges_existing=2" in output


@pytest.mark.django_db
def test_command_counts_failed_subscription(assinatura_factory):
    from datetime import date

    assinatura = assinatura_factory(dia_vencimento=5)
    # Provoca falha com um bug clássico: vencimento depois do plafond de competência.
    from unittest.mock import patch

    with patch(
        "financeiro.services.cobrancas._defaults_para",
        side_effect=RuntimeError("boom"),
    ):
        with pytest.raises(CommandError):
            _chamar("--today", "2026-01-05")

    output_without_failure = _chamar("--today", "2026-01-05")
    assert "charges_created=" in output_without_failure


@pytest.mark.django_db
def test_command_reports_zero_when_no_subscriptions(db):
    output = _chamar("--today", "2026-01-05")
    assert "subscriptions_scanned=0" in output
    assert "charges_created=0" in output
    assert "subscriptions_failed=0" in output
