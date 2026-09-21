import hashlib

from integracoes.api.exceptions import EnvelopeError


def version_for(instance):
    raw = f"{instance._meta.label_lower}:{instance.pk}:{instance.alterado_em.isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()


def etag_value(instance):
    return f'"{version_for(instance)}"'


def check_if_match(request, instance):
    """Exigido apenas para atualizações em modo SHARED.

    - Ausente → 409 version_header_missing.
    - Obsoleto → 409 VERSION_CONFLICT.
    """
    header = request.META.get("HTTP_IF_MATCH", "")
    if not header:
        raise EnvelopeError(409, "version_header_missing", "Header If-Match é obrigatório.")
    if header.strip('"') != version_for(instance):
        raise EnvelopeError(
            409,
            "VERSION_CONFLICT",
            "Versão obsoleta; recarregue o recurso e tente novamente.",
        )
    return header
