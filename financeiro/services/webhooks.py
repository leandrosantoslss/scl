from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from financeiro.models import Cobranca, EmissaoCobranca, Pagamento, EventoGateway
from financeiro.services.pagamentos import _atualizar_status_cobranca
from financeiro.selectors import saldo_cobranca
from portal.audit import registrar_evento_auditoria


def processar_evento_gateway(conta, event):
    """Roteia evento do provedor de negócios com eventos idênticos."""
    from django.db import IntegrityError

    try:
        with transaction.atomic():
            evento = EventoGateway.objects.create(
                conta=conta,
                provedor=conta.provedor,
                id_evento_externo=event.id_evento_externo,
                tipo=event.tipo,
                payload_hash=f"{event.id_evento_externo}-{event.ocorreu_em}",
                status=EventoGateway.Status.PROCESSADO,
                payload_protegido={
                    "tipo": event.tipo,
                    "id_referencia": event.id_referencia_externa,
                    "valor": str(event.valor or ""),
                },
            )
    except IntegrityError:
        # Evento repetido: devolve linha existente com padrão de duplicata.
        return EventoGateway.objects.get(
            provedor=conta.provedor, id_evento_externo=event.id_evento_externo
        ), True

    emissao = EmissaoCobranca.objects.filter(
        id_externo=event.id_referencia_externa, conta=conta
    ).first()

    if event.tipo == "paid":
        _processa_pagamento_gateway(emissao, event)
    return evento, False


def _processa_pagamento_gateway(emissao, event):
    if event.tipo != "paid":
        return None
    cobranca = emissao.cobranca
    locked = Cobranca.objects.select_for_update().get(pk=cobranca.pk)
    saldo = saldo_cobranca(locked)
    valor = Decimal(str(event.valor))
    if valor > saldo or valor <= 0:
        return None
    pagamento = Pagamento.objects.create(
        cobranca=locked,
        valor=valor,
        pago_em=timezone.now(),
        forma="gateway",
        origem=Pagamento.Origem.GATEWAY,
        status=Pagamento.Status.CONFIRMED,
        identificador_externo=event.id_referencia_externa,
        emissao_gateway=emissao,
        provedor_gateway=event.provedor,
    )
    _atualizar_status_cobranca(locked)
    registrar_evento_auditoria(
        acao="pagamento.gateway.registrado",
        objeto_tipo="financeiro.Pagamento",
        objeto_id=str(pagamento.pk),
        origem="integration",
        usuario=None,
    )
    return pagamento
