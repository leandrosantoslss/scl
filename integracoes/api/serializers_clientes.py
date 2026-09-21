from licencas.models import Cliente


CLIENTE_FIELDS = (
    "nome",
    "cnpjcpf",
    "email",
    "telefone",
    "cep",
    "endereco",
    "endnumero",
    "endbairro",
    "endcomplemento",
    "endUF",
    "endcidade",
    "endcodpais",
    "endpais",
    "bloqueado",
    "motivo_bloqueio",
)


def serializar_cliente(cliente, *, external_id=None, version_fn=None):
    from integracoes.api.etag import version_for

    payload = {}
    for campo in CLIENTE_FIELDS:
        valor = getattr(cliente, campo, None)
        if hasattr(valor, "isoformat"):
            valor = valor.isoformat()
        payload[campo] = valor
    payload.update(
        {
            "ativo": cliente.ativo,
            "external_id": external_id,
            "internal_id": cliente.pk,
            "version": version_for(cliente),
            "updated_at": cliente.alterado_em.isoformat() if cliente.alterado_em else None,
        }
    )
    return payload
