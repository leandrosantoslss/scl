from django.core.exceptions import ValidationError
from django.db import transaction

from portal.models import EventoAuditoria


SENSITIVE_KEYS = {
    "token",
    "client_secret",
    "authorization",
    "senha",
    "password",
    "secret",
    "document",
    "cnpjcpf",
    "cpf",
    "credencial",
}

ORIGINS = {"portal", "integration", "system"}

REDACTED = "[REDACTED]"


def _sanitize_fragment(payload):
    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise ValidationError("ANTES/DEPOIS devem ser dicionários.")
    return {
        key: (REDACTED if key.lower() in SENSITIVE_KEYS else value)
        for key, value in payload.items()
    }


def registrar_evento_auditoria(
    *,
    acao,
    objeto_tipo,
    objeto_id,
    antes=None,
    depois=None,
    origem,
    usuario=None,
    motivo=None,
    request_id=None,
    origem_identificador=None,
):
    if origem not in ORIGINS:
        raise ValidationError(f"Origem inválida: {origem!r}")

    return EventoAuditoria.objects.create(
        acao=acao,
        objeto_tipo=objeto_tipo,
        objeto_id=str(objeto_id),
        antes=_sanitize_fragment(antes),
        depois=_sanitize_fragment(depois),
        origem=origem,
        usuario=usuario if getattr(usuario, "is_authenticated", False) else None,
        motivo=motivo,
        request_id=request_id,
        origem_identificador=origem_identificador,
    )
