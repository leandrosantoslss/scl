from financeiro.selectors import saldo_cobranca
from integracoes.api.etag import version_for
from financeiro.models import Cobranca


def serializar_cobranca(cobranca, *, external_id=None):
    saldo = saldo_cobranca(cobranca)
    return {
        "external_id": external_id,
        "internal_id": cobranca.pk,
        "competencia": cobranca.competencia.isoformat(),
        "vencimento": cobranca.vencimento.isoformat(),
        "fim_carencia": cobranca.fim_carencia.isoformat(),
        "valor_original": str(cobranca.valor_original),
        "saldo": str(saldo),
        "status": cobranca.status,
        "origem": cobranca.origem,
        "version": version_for(cobranca),
        "updated_at": cobranca.alterado_em.isoformat() if cobranca.alterado_em else None,
    }


def serializar_pagamento(pagamento, external_id=None, *, integration=None):
    return {
        "internal_id": pagamento.pk,
        "external_id": external_id,
        "cobranca_internal_id": pagamento.cobranca_id,
        "valor": str(pagamento.valor),
        "forma": pagamento.forma,
        "origem": pagamento.origem,
        "status": pagamento.status,
        "version": version_for(pagamento),
        "updated_at": pagamento.alterado_em.isoformat() if pagamento.alterado_em else None,
    }

