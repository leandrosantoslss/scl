from django.core.exceptions import ValidationError
from django.db import transaction

from financeiro.gateways.base import (
    GatewayAuthenticationError,
    GatewayTemporaryError,
    GatewayValidationError as AdapterValidationError,
)
from financeiro.gateways.registry import get_adapter
from financeiro.models import Cobranca, EmissaoCobranca
from portal.audit import registrar_evento_auditoria


def _comando_para(cobranca, meio, idempotencia):
    cliente = cobranca.assinatura.cliente
    return {
        "cobranca_id": cobranca.pk,
        "valor": cobranca.valor_original,
        "vencimento": cobranca.vencimento.isoformat(),
        "documento_pagador": str(cliente.cnpjcpf),
        "nome_pagador": cliente.nome,
        "end_pagador": f"{cliente.endereco}, {cliente.endnumero}",
        "meio": meio,
        "idempotencia": idempotencia,
    }


def _validar(cobranca, conta, meio, idempotencia):
    if not conta.ativo:
        raise ValidationError("Conta de gateway inativa.")
    if meio == "pix" and not conta.habilita_pix:
        raise ValidationError("PIX não habilitado nesta conta.")
    if meio == "boleto" and not conta.habilita_boleto:
        raise ValidationError("Boleto não habilitado nesta conta.")
    if cobranca.status in (Cobranca.Status.CANCELADA, Cobranca.Status.PAGA):
        raise ValidationError("Cobrança cancelada/paga não aceita nova emissão.")
    if existe_emissao_ativa(cobranca):
        raise ValidationError("Já existe emissão ativa para esta cobrança.")


def existe_emissao_ativa(cobranca):
    estados = (EmissaoCobranca.Status.REQUESTED, EmissaoCobranca.Status.ISSUED)
    return EmissaoCobranca.objects.filter(
        cobranca=cobranca, status__in=estados
    ).exists()


def _status(status_externo):
    mapa = {
        "issued": EmissaoCobranca.Status.ISSUED,
        "failed": EmissaoCobranca.Status.FAILED,
        "pending_unknown": EmissaoCobranca.Status.PENDING_UNKNOWN,
        "cancelled": EmissaoCobranca.Status.CANCELLED,
        "paid": EmissaoCobranca.Status.PAID,
        "requested": EmissaoCobranca.Status.REQUESTED,
    }
    return mapa.get(status_externo, EmissaoCobranca.Status.PENDING_UNKNOWN)


def _auditar(objeto, *, acao, usuario, motivo=None):
    return registrar_evento_auditoria(
        acao=acao,
        objeto_tipo=f"{objeto._meta.app_label}.{objeto.__class__.__name__}",
        objeto_id=str(objeto.pk),
        origem="portal",
        usuario=usuario,
        motivo=motivo,
    )


@transaction.atomic
def emitir_cobranca(cobranca, *, conta, meio, idempotencia, usuario):
    """Duas fases: emissão no DB (requested) e chamada do adaptador fora do lock."""
    cobranca = Cobranca.objects.select_for_update().get(pk=cobranca.pk)
    _validar(cobranca, conta, meio, idempotencia)

    emissao = EmissaoCobranca.objects.create(
        cobranca=cobranca,
        conta=conta,
        meio=meio,
        chave_idempotencia=idempotencia,
        status=EmissaoCobranca.Status.REQUESTED,
    )

    adaptador = get_adapter(conta)
    comando = _comando_para(cobranca, meio, idempotencia)

    try:
        resultado = adaptador.issue(comando)
    except AdapterValidationError as erro:
        emissao.status = EmissaoCobranca.Status.FAILED
        emissao.erro_normalizado = str(erro)
        emissao.save()
        return emissao
    except GatewayAuthenticationError as erro:
        emissao.status = EmissaoCobranca.Status.FAILED
        emissao.erro_normalizado = f"Credenciais de gateway: {erro}"
        emissao.save()
        return emissao
    except GatewayTemporaryError:
        emissao.status = EmissaoCobranca.Status.PENDING_UNKNOWN
        emissao.erro_normalizado = (
            "Resultado indefinido do provedor (timeout/conexão interrompida)."
        )
        emissao.save()
        return emissao

    emissao.id_externo = resultado.external_id
    emissao.status = _status(resultado.status)
    emissao.meio = resultado.method
    emissao.pix_copia_e_cola = resultado.pix_copy_paste
    emissao.boleto_url = resultado.presentation_url
    emissao.linha_digitavel = resultado.digitable_line
    emissao.save()
    from portal.models import EventoAuditoria

    _auditar(emissao, acao="emissao.cobranca.emitida", usuario=usuario)
    return emissao


def cancelar_emissao(emissao, *, idempotencia, usuario):
    """Cancela emissão ativa; não marca cancelada quando o provedor rejeita."""
    estados = (EmissaoCobranca.Status.REQUESTED, EmissaoCobranca.Status.ISSUED)
    emissao = EmissaoCobranca.objects.select_for_update().get(pk=emissao.pk)
    if emissao.status not in estados:
        raise ValidationError("Apenas emissão emitida/pedida pode ser cancelada.")

    adaptador = get_adapter(emissao.conta)
    resultado_cancel = adaptador.cancel(emissao.id_externo, idempotencia=idempotencia)

    if resultado_cancel.status == "cancelled":
        emissao.status = EmissaoCobranca.Status.CANCELLED
        emissao.save()
        _auditar(emissao, acao="emissao.cobranca.cancelada", usuario=usuario)
    elif resultado_cancel.status == "unknown":
        emissao.erro_normalizado = "Resultado indefinido do provedor durante cancelamento."
        emissao.save()
        raise ValidationError("Resultado indefinido; consulte o provedor antes de prosseguir.")

    return emissao
