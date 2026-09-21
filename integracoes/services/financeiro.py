from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from financeiro.models import Cobranca, Pagamento
from financeiro.selectors import saldo_cobranca
from portal.audit import registrar_evento_auditoria


def _auditar(objeto, *, acao, usuario, motivo=None):
    return registrar_evento_auditoria(
        acao=acao,
        objeto_tipo=f"{objeto._meta.app_label}.{objeto.__class__.__name__}",
        objeto_id=objeto.pk,
        origem="integration",
        usuario=None,
        motivo=motivo,
        depois={"id_publico": getattr(objeto, "public_id", None) and str(objeto.public_id)},
    )


@transaction.atomic
def criar_cobranca_legado(*, assinatura, payload, integration, usuario):
    """Cobrança externa somente para assinatura sob origem legada."""
    from integracoes.models import AssinaturaOrigemCobranca

    if not AssinaturaOrigemCobranca.objects.filter(assinatura=assinatura).exists():
        raise ValidationError(
            {"assinatura": "Apenas assinatura com origem legada aceita cobrança externa."}
        )

    valor = Decimal(str(payload.get("valor_original")))
    if valor <= 0:
        raise ValidationError({"valor_original": "O valor deve ser positivo."})

    competencia = _data(payload.get("competencia"))
    vencimento = _data(payload.get("vencimento"))
    fim_carencia = _data(payload.get("fim_carencia"))

    try:
        cobranca = Cobranca.objects.create(
            assinatura=assinatura,
            competencia=competencia,
            vencimento=vencimento,
            fim_carencia=fim_carencia,
            valor_original=valor,
            status=Cobranca.Status.ABERTA,
            origem="legacy",
            descricao=payload.get("descricao", ""),
        )
    except IntegrityError:
        raise ValidationError({"cobranca.competencia": "Ciclo já existe nesta assinatura."})

    from integracoes.models import CobrancaReferenciaExterna

    CobrancaReferenciaExterna.objects.create(
        integration=integration,
        external_id=payload.get("external_id", ""),
        cobranca=cobranca,
    )
    _auditar(cobranca, acao="cobranca.criada.legado", usuario=usuario, motivo="via API legada")
    return cobranca


@transaction.atomic
def registrar_pagamento_legado(*, cobranca, payload, integration):
    locked = Cobranca.objects.select_for_update().get(pk=cobranca.pk)
    if locked.status == Cobranca.Status.CANCELADA:
        raise ValidationError("Cobrança cancelada não aceita pagamentos.")
    saldo = saldo_cobranca(locked)
    valor = Decimal(str(payload.get("valor")))
    if valor <= 0 or valor > saldo:
        raise ValidationError("Valor deve ser positivo e não pode exceder o saldo.")

    identificador = payload.get("identificador_externo") or payload.get("external_id", "")

    pagamento = Pagamento.objects.create(
        cobranca=cobranca,
        valor=valor,
        pago_em=payload.get("pago_em", timezone.now()),
        forma=payload.get("forma", "pix"),
        origem=Pagamento.Origem.LEGACY,
        status=Pagamento.Status.CONFIRMED,
        identificador_externo=identificador,
        integracao=integration,
    )

    from financeiro.services.pagamentos import _atualizar_status_cobranca

    _atualizar_status_cobranca(locked)

    if identificador:
        from integracoes.models import PagamentoReferenciaExterna

        PagamentoReferenciaExterna.objects.get_or_create(
            integration=integration,
            external_id=identificador,
            pagamento=pagamento,
        )
    _auditar(pagamento, acao="pagamento.registrado.legado", usuario=None, motivo="via API legada")
    return pagamento


@transaction.atomic
def estornar_pagamento_legado(*, pagamento, motivo, integration):
    if pagamento.integracao_id != integration.id:
        raise ValidationError("Não autorizado: estilo pagamento não é desta integração.")

    locked_pagamento = Pagamento.objects.select_for_update().get(pk=pagamento.pk)
    locked_cobranca = Cobranca.objects.select_for_update().get(pk=locked_pagamento.cobranca_id)

    if locked_pagamento.status == Pagamento.Status.REVERSED:
        raise ValidationError("Pagamento já estornado.")
    locked_pagamento.status = Pagamento.Status.REVERSED
    locked_pagamento.estornado_em = timezone.now()
    locked_pagamento.motivo_estorno = motivo
    locked_pagamento.save()

    from financeiro.services.pagamentos import _atualizar_status_cobranca as _upd

    _upd(locked_cobranca)
    _auditar(locked_pagamento, acao="pagamento.estornado.legado", usuario=None, motivo=motivo)
    return locked_pagamento


@transaction.atomic
def cancelar_cobranca_legado(*, cobranca, integration, motivo):
    locked = Cobranca.objects.select_for_update().get(pk=cobranca.pk)
    if locked.origem != "legacy":
        raise ValidationError("Apenas cobranças legadas são canceladas pela integração.")
    if saldo_cobranca(locked) < locked.valor_original:
        raise ValidationError("Cobrança paga não pode ser cancelada.")
    if not (motivo or "").strip():
        raise ValidationError("Motivo é obrigatório.")
    locked.status = Cobranca.Status.CANCELADA
    locked.motivo_cancelamento = motivo
    locked.save(update_fields=["status", "motivo_cancelamento"])
    _auditar(locked, acao="cobranca.cancelada.legado", usuario=None, motivo=motivo)
    return locked




def _data(valor):
    if isinstance(valor, _date):
        return valor
    year, month, day = (int(p) for p in str(valor).split("-"))
    return _date(year, month, day)


from datetime import date as _date  # noqa: E402
