from integracoes.api.exceptions import IntegrationPermissionDenied
from integracoes.models import AuthorityMode, PoliticaIntegracao, Recurso
from portal.audit import registrar_evento_auditoria


RECURSO_POR_MODELO = {
    "licencas.Cliente": Recurso.CLIENTE,
    "licencas.ClienteSistema": Recurso.ASSINATURA,
    "financeiro.Cobranca": Recurso.COBRANCA,
    "financeiro.Pagamento": Recurso.PAGAMENTO,
}


def _politica(integration, *, resource):
    return integration.politicas.filter(recurso=resource).first()


def authorize_fields(integration, *, resource, operation, fields):
    """Matriz de autoridade por recurso; nunca tenta adivinhar permissões."""
    fields_set = set(fields)
    if resource not in Recurso.values:
        raise IntegrationPermissionDenied(f"Recurso desconhecido: {resource}")
    if operation not in ("read", "write"):
        raise IntegrationPermissionDenied(f"Operação desconhecida: {operation}")

    politica = _politica(integration, resource=resource)
    if politica is None:
        raise IntegrationPermissionDenied(
            f"Sem política definida para {resource} nesta integração."
        )

    if operation == "read":
        campos = set(politica.readable_fields or [])
        if "*" in campos:
            return campos
        nao_listados = fields_set - campos
        if nao_listados:
            raise IntegrationPermissionDenied(
                f"Campos de leitura não autorizados: {sorted(nao_listados)}"
            )
        return campos

    if politica.modo == AuthorityMode.SCL_MASTER:
        raise IntegrationPermissionDenied(
            f"Escrita externa bloqueada: {resource} é SCL_MASTER."
        )

    permitidos = set(politica.writable_fields or [])
    nao_listados = fields_set - permitidos
    if nao_listados:
        raise IntegrationPermissionDenied(
            f"Campos de escrita não autorizados: {sorted(nao_listados)}"
        )
    return permitidos.intersection(fields_set)


def campos_sob_authoridade(modelo_cls, campos, modo):
    """Subconjunto de `campos` governados por políticas no modo indicado."""
    recurso = RECURSO_POR_MODELO[f"{modelo_cls._meta.app_label}.{modelo_cls.__name__}"]
    politicas = PoliticaIntegracao.objects.filter(recurso=recurso, modo=modo)
    conjunto = set()
    for politica in politicas.iterator():
        conjunto.update(politica.writable_fields or [])
    return conjunto.intersection(set(campos))


def campos_sob_authoridade_legado(modelo_cls, campos):
    return campos_sob_authoridade(modelo_cls, campos, AuthorityMode.LEGACY_MASTER)


def salvar_politica(*, integration, resource, modo, readable_fields=None, writable_fields=None, usuario, motivo=None):
    politica, _criada = PoliticaIntegracao.objects.get_or_create(
        integration=integration,
        recurso=resource,
        defaults={
            "modo": modo,
            "readable_fields": readable_fields or [],
            "writable_fields": writable_fields or [],
        },
    )
    politica.modo = modo
    if readable_fields is not None:
        politica.readable_fields = readable_fields
    if writable_fields is not None:
        politica.writable_fields = writable_fields
    politica.save()
    registrar_evento_auditoria(
        acao="integracao.politica.alterada",
        objeto_tipo="integracoes.PoliticaIntegracao",
        objeto_id=str(politica.pk),
        origem="portal",
        usuario=usuario,
        motivo=motivo,
        depois={"modo": modo, "recurso": resource},
    )
    return politica
