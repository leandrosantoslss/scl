from decimal import Decimal

from django.db.models import Count, DecimalField, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from financeiro.models import Cobranca, Pagamento
from licencas.models import Cliente, ClienteSistema, Sistema


STATUS_LABELS = {
    Cobranca.Status.ABERTA: "Em aberto",
    Cobranca.Status.PAGA: "Paga",
    Cobranca.Status.CANCELADA: "Cancelada",
}


def dashboard_metrics(request):
    hoje = timezone.localdate()

    clientes_total = Cliente.objects.count()
    sistemas_total = Sistema.objects.count()
    assinaturas_ativas = ClienteSistema.objects.filter(ativo=True).count()

    status_counts = {codigo: 0 for codigo in Cobranca.Status.values}
    for row in Cobranca.objects.values("status").annotate(total=Count("id")):
        status_counts[row["status"]] = row["total"]

    cobrancas_abertas = status_counts[Cobranca.Status.ABERTA]
    cobrancas_pagas = status_counts[Cobranca.Status.PAGA]
    cobrancas_canceladas = status_counts[Cobranca.Status.CANCELADA]

    totais = Cobranca.objects.filter(status=Cobranca.Status.ABERTA).aggregate(
        valor_aberto=Sum(
            "valor_original", output_field=DecimalField(max_digits=12, decimal_places=2)
        ),
        vencidas=Count("id", filter=Q(vencimento__lt=hoje)),
    )
    valor_total = Decimal(str(totais["valor_aberto"] or "0.00"))
    cobrancas_vencidas = totais["vencidas"] or 0

    recebido = Pagamento.objects.filter(
        status=Pagamento.Status.CONFIRMED,
        pago_em__month=hoje.month,
        pago_em__year=hoje.year,
    ).aggregate(total=Sum("valor", output_field=DecimalField(max_digits=12, decimal_places=2)))
    valor_recebido = Decimal(str(recebido["total"] or "0.00"))

    status_items = [
        {"label": STATUS_LABELS[codigo], "value": status_counts[codigo]}
        for codigo in Cobranca.Status.values
    ]
    status_values = [item["value"] for item in status_items]

    por_mes = (
        Cobranca.objects.annotate(mes=TruncMonth("competencia"))
        .values("mes")
        .annotate(total=Count("id"))
        .order_by("mes")[:12]
    )
    charge_months = [row["mes"].strftime("%Y-%m") for row in por_mes]
    charge_values = [row["total"] for row in por_mes]

    return {
        "clientes_total": clientes_total,
        "sistemas_total": sistemas_total,
        "assinaturas_ativas": assinaturas_ativas,
        "cobrancas_abertas": cobrancas_abertas,
        "cobrancas_abertas_count": cobrancas_abertas,
        "cobrancas_pagas": cobrancas_pagas,
        "cobrancas_pagas_count": cobrancas_pagas,
        "cobrancas_canceladas_count": cobrancas_canceladas,
        "cobrancas_vencidas": cobrancas_vencidas,
        "valor_em_aberto": _formato(valor_total),
        "valor_recebido_mes": _formato(valor_recebido),
        "valor_recebido_mes_curt": _formato_curt(valor_recebido),
        "status_items": status_items,
        "status_values": status_values,
        "charge_months": charge_months,
        "charge_values": charge_values,
        "last_update": timezone.localtime().strftime("%d/%m/%Y %H:%M"),
    }


def _formato(valor):
    texto = f"{Decimal(str(valor)):,.2f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def _formato_curt(valor):
    return _formato(valor).split(",")[0]
