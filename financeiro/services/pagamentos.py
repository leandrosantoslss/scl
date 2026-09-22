from core.notifications import notify_users
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
        origem="portal",
        usuario=usuario,
        motivo=motivo,
    )


@transaction.atomic
def registrar_pagamento_manual(*, cobranca, valor, pago_em, forma, usuario):
    locked = Cobranca.objects.select_for_update().get(pk=cobranca.pk)
    if locked.status == Cobranca.Status.CANCELADA:
        raise ValidationError("Cobrança cancelada não aceita pagamentos.")
    saldo = saldo_cobranca(locked)
    valor_decimal = Decimal(str(valor))
    if valor_decimal <= 0 or valor_decimal > saldo:
        raise ValidationError(
            "O valor deve ser positivo e não pode exceder o saldo."
        )

    pagamento = Pagamento.objects.create(
        cobranca=locked,
        valor=valor_decimal,
        pago_em=pago_em,
        forma=forma,
        origem=Pagamento.Origem.MANUAL,
        status=Pagamento.Status.CONFIRMED,
        usuario=usuario,
    )

    _atualizar_status_cobranca(locked)
    _auditar(pagamento, acao="pagamento.registrado", usuario=usuario)
    notify_users(
        "Pagamento registrado",
        f"Cobrança {cobranca.competencia} recebeu R$ {valor_decimal} de {forma}",
        "",
    )
    return pagamento


def _atualizar_status_cobranca(locked):
    if locked.status == Cobranca.Status.CANCELADA:
        return
    locked.status = Cobranca.Status.PAGA if saldo_cobranca(locked) <= 0 else Cobranca.Status.ABERTA
    locked.save(update_fields=["status"])


@transaction.atomic
def estornar_pagamento(*, pagamento, motivo, usuario):
    if not (motivo or "").strip():
        raise ValidationError({"motivo_estorno": "Informe o motivo do estorno."})

    locked_pagamento = Pagamento.objects.select_for_update().get(pk=pagamento.pk)
    if locked_pagamento.status == Pagamento.Status.REVERSED:
        raise ValidationError("Pagamento já estornado.")

    locked_cobranca = Cobranca.objects.select_for_update().get(pk=locked_pagamento.cobranca_id)

    locked_pagamento.status = Pagamento.Status.REVERSED
    locked_pagamento.estornado_por = usuario
    locked_pagamento.estornado_em = timezone.now()
    locked_pagamento.motivo_estorno = motivo
    locked_pagamento.save()

    _atualizar_status_cobranca(locked_cobranca)
    _auditar(locked_pagamento, acao="pagamento.estornado", usuario=usuario, motivo=motivo)
    notify_users(
        "Pagamento estornado",
        f"Cobrança {locked_cobranca.competencia}: R$ {locked_pagamento.valor} estornado ({motivo})",
        "",
    )
    return locked_pagamento


@transaction.atomic
def cancelar_cobranca_scl(*, cobranca, motivo, usuario):
    if not (motivo or "").strip():
        raise ValidationError({"motivo_cancelamento": "Informe o motivo do cancelamento."})

    locked = Cobranca.objects.select_for_update().get(pk=cobranca.pk)
    if locked.origem != "scl":
        raise ValidationError("Apenas cobranças de origem SCL podem ser canceladas no portal.")
    if locked.status == Cobranca.Status.CANCELADA:
        raise ValidationError("Cobrança já cancelada.")
    if saldo_cobranca(locked) < locked.valor_original:
        raise ValidationError("Cobrança com pagamento confirmado não pode ser cancelada.")

    from licencas.models import ClienteSistema  # noqa: F401  (proveniência futura de emissão)

    locked.status = Cobranca.Status.CANCELADA
    locked.cancelada_por = usuario
    locked.cancelada_em = timezone.now()
    locked.motivo_cancelamento = motivo
    locked.save()
    _auditar(locked, acao="cobranca.cancelada", usuario=usuario, motivo=motivo)
    notify_users(
        "Cobrança cancelada",
        f"Cobrança {locked.competencia} de {locked.assinatura.cliente.nome} cancelada ({motivo})",
        "",
    )
    return locked
