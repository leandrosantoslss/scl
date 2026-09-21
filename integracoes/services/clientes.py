from django.db import transaction

from integracoes.services import references
from integracoes.services.portal_authority import rejeitar_campos_protegidos
from licencas.models import Cliente
from licencas.validators import validate_document
from portal.audit import registrar_evento_auditoria


def _auditar(objeto, *, acao, usuario, motivo=None):
    return registrar_evento_auditoria(
        acao=acao,
        objeto_tipo=f"{objeto._meta.app_label}.{objeto.__class__.__name__}",
        objeto_id=objeto.pk,
        origem="portal",
        usuario=usuario,
    )


def _validar_campo_documento(cnpjcpf):
    validate_document(cnpjcpf)


def criar_cliente_api(dados, integration, external_id, usuario):
    """Criação atômica: cliente + referência externa (MESMA transação)."""
    with transaction.atomic():
        cliente = Cliente(**dados)
        cliente.cnpjcpf = (cliente.cnpjcpf or "").strip()
        cliente.full_clean()
        validate_document(cliente.cnpjcpf)
        cliente.save()
        _auditar(cliente, acao="cliente.criado", usuario=usuario)
        references.obter_ou_criar_referencia(
            Cliente, integration=integration, external_id=external_id, objeto=cliente
        )
    return cliente


def atualizar_cliente_api(cliente, payload, integration, external_id, usuario):
    """PATCH atômico: cliente + referência (MESMA transação)."""
    with transaction.atomic():
        rejeitar_campos_protegidos(Cliente, set(payload.keys()))
        locked = Cliente.objects.select_for_update().get(pk=cliente.pk)
        for campo, valor in payload.items():
            setattr(locked, campo, valor)
        locked.full_clean()
        locked.save()
        _auditar(locked, acao="cliente.atualizado", usuario=usuario)
        if external_id:
            references.obter_ou_criar_referencia(
                Cliente, integration=integration, external_id=external_id, objeto=locked
            )
    return locked
