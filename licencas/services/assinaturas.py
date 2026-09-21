from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from integracoes.services.portal_authority import rejeitar_campos_protegidos
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
def criar_assinatura(*, form, usuario):
    with transaction.atomic():
        assinatura = form.save(commit=False)
        assinatura.full_clean()
        assinatura.save()
        _auditar(assinatura, acao="assinatura.criada", usuario=usuario)
        return assinatura


@transaction.atomic
def atualizar_comercial_form(assinatura, *, form, usuario):
    from licencas.models import ClienteSistema as _Model

    locked = _Model.objects.select_for_update().get(pk=assinatura.pk)
    rejeitar_campos_protegidos(_Model, set(form.cleaned_data.keys()))
    for field, value in form.cleaned_data.items():
        setattr(locked, field, value)
    locked.full_clean()
    locked.save()
    _auditar(locked, acao="assinatura.valor_atualizado", usuario=usuario)
    return locked


@transaction.atomic
def atualizar_comercial(assinatura, *, valor_recorrente, usuario, motivo=None):
    locked = assinatura.__class__.objects.select_for_update().get(pk=assinatura.pk)
    novo_valor = Decimal(str(valor_recorrente))
    if novo_valor <= Decimal("0"):
        raise ValidationError(
            {"valor_recorrente": "O valor recorrente deve ser positivo."}
        )
    locked.valor_recorrente = novo_valor
    locked.full_clean()
    locked.save(update_fields=["valor_recorrente"])
    _auditar(locked, acao="assinatura.valor_atualizado", usuario=usuario, motivo=motivo)
    return locked


@transaction.atomic
def ativar_assinatura(assinatura, *, usuario):
    locked = assinatura.__class__.objects.select_for_update().get(pk=assinatura.pk)
    if locked.valor_recorrente is None or locked.valor_recorrente <= Decimal("0"):
        raise ValidationError(
            {"valor_recorrente": "Prossiga com valor positivo antes de ativar."}
        )
    if not locked.periodicidade:
        raise ValidationError({"periodicidade": "Periodicidade obrigatória para ativar."})
    if locked.primeiro_vencimento is None:
        raise ValidationError(
            {"primeiro_vencimento": "Primeiro vencimento obrigatório para ativar."}
        )
    locked.ativo = True
    locked.full_clean()
    locked.save(update_fields=["ativo"])
    _auditar(locked, acao="assinatura.ativada", usuario=usuario)
    return locked


@transaction.atomic
def bloquear_assinatura(assinatura, *, motivo, usuario):
    if not (motivo or "").strip():
        raise ValidationError({"motivo_bloqueio": "Informe o motivo do bloqueio."})
    locked = assinatura.__class__.objects.select_for_update().get(pk=assinatura.pk)
    locked.bloqueado = True
    locked.motivo_bloqueio = motivo
    locked.bloqueado_em = timezone.now()
    locked.full_clean()
    locked.save(update_fields=["bloqueado", "motivo_bloqueio", "bloqueado_em"])
    _auditar(locked, acao="assinatura.bloqueada", usuario=usuario, motivo=motivo)
    return locked


@transaction.atomic
def desbloquear_assinatura(assinatura, *, usuario):
    locked = assinatura.__class__.objects.select_for_update().get(pk=assinatura.pk)
    locked.bloqueado = False
    locked.motivo_bloqueio = ""
    locked.bloqueado_em = None
    locked.full_clean()
    locked.save(update_fields=["bloqueado", "motivo_bloqueio", "bloqueado_em"])
    _auditar(locked, acao="assinatura.desbloqueada", usuario=usuario)
    return locked


@transaction.atomic
def desativar_assinatura(assinatura, *, motivo, usuario):
    locked = assinatura.__class__.objects.select_for_update().get(pk=assinatura.pk)
    locked.bloqueado = False
    locked.motivo_bloqueio = ""
    locked.bloqueado_em = None
    locked.ativo = False
    locked.full_clean()
    locked.save(update_fields=["ativo", "bloqueado", "motivo_bloqueio", "bloqueado_em"])
    _auditar(locked, acao="assinatura.desativada", usuario=usuario, motivo=motivo)
    return locked
