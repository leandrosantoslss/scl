from django.core.exceptions import ValidationError
from django.db import transaction

from financeiro.crypto import encrypt_config
from portal.audit import registrar_evento_auditoria


REQUIRED_KEYS = {
    "efi": {"client_id", "client_secret"},
    "sicredi": {"chave_acesso", "client_id", "client_secret"},
    "sicoob": {"client_id", "client_secret"},
}


def _auditar_conta(conta, *, acao, usuario, motivo=None, campos=None):
    return registrar_evento_auditoria(
        acao=acao,
        objeto_tipo="financeiro.ContaGateway",
        objeto_id=str(conta.public_id),
        origem="portal",
        usuario=usuario,
        motivo=motivo,
        depois={"campos_atualizados": sorted(campos)} if campos is not None else None,
    )


def chaves_obrigatorias(provedor):
    return REQUIRED_KEYS.get(provedor, set())


def validar_configuracao(conta, configuracao):
    """Chaves obrigatórias por provedor; valores nunca são devolvidos."""
    faltantes = chaves_obrigatorias(conta.provedor) - set(configuracao.keys())
    if faltantes:
        raise ValidationError(
            {
                "configuracao_criptografada": f"Chaves ausentes para {conta.provedor}: {sorted(faltantes)}"
            }
        )


@transaction.atomic
def salvar_credenciais(conta, *, configuracao, usuario):
    validar_configuracao(conta, configuracao)

    ciphertext = encrypt_config(configuracao)
    conta.configuracao_criptografada = ciphertext
    conta.alterado_por = usuario
    conta.full_clean()
    conta.save()

    _auditar_conta(
        conta,
        acao="conta_gateway.credenciais.salvas",
        usuario=usuario,
        campos=sorted(configuracao.keys()),
    )
    return conta


@transaction.atomic
def ativar_conta(conta, *, usuario):
    conta.ativo = True
    conta.full_clean()
    conta.save(update_fields=["ativo"])
    _auditar_conta(conta, acao="conta_gateway.ativada", usuario=usuario)
    return conta


@transaction.atomic
def desativar_conta(conta, *, usuario, motivo=None):
    conta.ativo = False
    conta.full_clean()
    conta.save(update_fields=["ativo"])
    _auditar_conta(conta, acao="conta_gateway.desativada", usuario=usuario, motivo=motivo)
    return conta
