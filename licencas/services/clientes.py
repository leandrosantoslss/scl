from django.db import transaction
from django.utils import timezone

from integracoes.services.portal_authority import rejeitar_campos_protegidos
from licencas.models import Sistema
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


def criar_cliente(*, form, usuario):
    with transaction.atomic():
        cliente = form.save(commit=False)
        cliente.full_clean()
        cliente.save()
        _auditar(cliente, acao="cliente.criado", usuario=usuario)
        return cliente


@transaction.atomic
def atualizar_cliente(cliente, *, form, usuario):
    from licencas.models import Cliente as _Cliente

    locked = _Cliente.objects.select_for_update().get(pk=cliente.pk)
    rejeitar_campos_protegidos(_Cliente, set(form.cleaned_data.keys()))
    for field, value in form.cleaned_data.items():
        if field == "codigo":
            continue
        setattr(locked, field, value)
    locked.full_clean()
    locked.save()
    _auditar(locked, acao="cliente.atualizado", usuario=usuario)
    return locked


@transaction.atomic
def bloquear_cliente(cliente, *, motivo, usuario):
    cliente = Cliente.objects.select_for_update().get(pk=cliente.pk)
    cliente.bloqueado = True
    cliente.motivo_bloqueio = motivo
    cliente.bloqueado_em = timezone.now()
    cliente.full_clean()
    cliente.save(update_fields=["bloqueado", "motivo_bloqueio", "bloqueado_em"])
    _auditar(cliente, acao="cliente.bloqueado", usuario=usuario, motivo=motivo)
    return cliente


@transaction.atomic
def desbloquear_cliente(cliente, *, usuario):
    cliente = Cliente.objects.select_for_update().get(pk=cliente.pk)
    cliente.bloqueado = False
    cliente.motivo_bloqueio = ""
    cliente.bloqueado_em = None
    cliente.full_clean()
    cliente.save(update_fields=["bloqueado", "motivo_bloqueio", "bloqueado_em"])
    _auditar(cliente, acao="cliente.desbloqueado", usuario=usuario)
    return cliente


def criar_sistema(*, form, usuario):
    with transaction.atomic():
        sistema = form.save(commit=False)
        sistema.full_clean()
        sistema.save()
        _auditar(sistema, acao="sistema.criado", usuario=usuario)
        return sistema


@transaction.atomic
def atualizar_sistema(sistema, *, form, usuario):
    locked = Sistema.objects.select_for_update().get(pk=sistema.pk)
    form.cleaned_data["codigo"] = sistema.codigo  # codigo é imutável
    rejeitar_campos_protegidos(Sistema, set(form.cleaned_data.keys()))
    for field, value in form.cleaned_data.items():
        setattr(locked, field, value)
    locked.full_clean()
    locked.save()
    _auditar(locked, acao="sistema.atualizado", usuario=usuario)
    return locked
