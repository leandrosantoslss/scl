from licencas.models import ClienteSistema


CLIENTE_SISTEMA_FIELDS = (
    "valor_recorrente",
    "periodicidade",
    "data_inicio",
    "primeiro_vencimento",
    "dia_vencimento",
    "dias_carencia",
    "bloqueado",
    "motivo_bloqueio",
)


def serializar_assinatura(assinatura, *, external_id=None, versao_fn=None):
    from integracoes.api.etag import version_for

    payload = {}
    for campo in CLIENTE_SISTEMA_FIELDS:
        valor = getattr(assinatura, campo, None)
        if hasattr(valor, "isoformat"):
            valor = valor.isoformat()
        elif valor is not None and hasattr(valor, "__int__") and not isinstance(valor, (int, float)):
            valor = str(valor)
        payload[campo] = valor
    payload.update(
        {
            "ativo": assinatura.ativo,
            "external_id": external_id,
            "internal_id": assinatura.pk,
            "version": version_for(assinatura),
            "updated_at": assinatura.alterado_em.isoformat() if assinatura.alterado_em else None,
        }
    )
    return payload
