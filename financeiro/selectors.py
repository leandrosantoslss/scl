from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db.models import Sum

from financeiro.models import Cobranca, Pagamento


@dataclass(frozen=True)
class FinancialPosition:
    code: str
    allowed: bool
    oldest_due_date: date | None
    grace_ends_on: date | None
    outstanding_amount: Decimal


def saldo_cobranca(cobranca):
    """Saldo em aberto: apenas pagamentos `confirmed` somam."""
    confirmado = (
        Pagamento.objects.filter(
            cobranca=cobranca, status=Pagamento.Status.CONFIRMED
        ).aggregate(total=Sum("valor"))["total"]
        or Decimal("0.00")
    )
    return cobranca.valor_original - confirmado


def obter_posicao_financeira(assinatura, *, hoje):
    """Posição financeira derivada; nunca persistida.

    - CANCELADAS nunca contribuem para saldo, carência ou bloqueio.
    - Estornados contribuem zero: apenas `confirmed` é somado.
    """
    cobrancas = list(
        Cobranca.objects.filter(
            assinatura=assinatura, status=Cobranca.Status.ABERTA
        ).order_by("vencimento", "pk")
    )

    pendentes = []
    outstanding = Decimal("0.00")
    for cobranca in cobrancas:
        saldo = saldo_cobranca(cobranca)
        if saldo > 0:
            pendentes.append(cobranca)
            outstanding += saldo

    if not pendentes:
        return FinancialPosition("CURRENT", True, None, None, Decimal("0.00"))

    mais_atrasada = pendentes[0]
    if hoje <= mais_atrasada.vencimento:
        return FinancialPosition("CURRENT", True, None, None, outstanding)
    if hoje <= mais_atrasada.fim_carencia:
        return FinancialPosition(
            "OVERDUE_IN_GRACE",
            True,
            mais_atrasada.vencimento,
            mais_atrasada.fim_carencia,
            outstanding,
        )
    return FinancialPosition(
        "DELINQUENT",
        False,
        mais_atrasada.vencimento,
        mais_atrasada.fim_carencia,
        outstanding,
    )
