from django.db import IntegrityError, transaction

from integracoes.api.exceptions import IntegrationConflict, IntegrationPermissionDenied
from integracoes.models import (
    AssinaturaReferenciaExterna,
    ClienteReferenciaExterna,
    CobrancaReferenciaExterna,
    IntegracaoLegado,
    PagamentoReferenciaExterna,
    RequisicaoIntegracao,
)
from portal.audit import registrar_evento_auditoria


MODEL_REFERENCIA = {
    "licencas.Cliente": ClienteReferenciaExterna,
    "licencas.ClienteSistema": AssinaturaReferenciaExterna,
    "financeiro.Cobranca": CobrancaReferenciaExterna,
    "financeiro.Pagamento": PagamentoReferenciaExterna,
}

FK_NOME = {
    ClienteReferenciaExterna: "cliente",
    AssinaturaReferenciaExterna: "assinatura",
    CobrancaReferenciaExterna: "cobranca",
    PagamentoReferenciaExterna: "pagamento",
}


def _classe_para(modelo_cls):
    return MODEL_REFERENCIA[f"{modelo_cls._meta.app_label}.{modelo_cls.__name__}"]


def resolve_external_reference(modelo_cls, integration, external_id):
    classe = _classe_para(modelo_cls)
    fk = FK_NOME[classe]
    try:
        referencia = classe.objects.get(integration=integration, external_id=external_id)
    except classe.DoesNotExist:
        return None, None
    return referencia, getattr(referencia, fk)


def obter_ou_criar_referencia(modelo_cls, *, integration, external_id, objeto):
    classe = _classe_para(modelo_cls)
    fk = FK_NOME[classe]
    try:
        with transaction.atomic():
            return classe.objects.get_or_create(
                integration=integration,
                external_id=external_id,
                defaults={fk: objeto},
            )
    except IntegrityError:
        return classe.objects.get(integration=integration, external_id=external_id), False


def transferir_propriedade_referencia(
    referencia, *, nova_integracao: IntegracaoLegado, usuario, motivo
):
    if not (motivo or "").strip():
        raise IntegrationPermissionDenied("transferência exige motivo")

    classe = type(referencia)
    fk = FK_NOME[classe]
    with transaction.atomic():
        antiga = classe.objects.select_for_update().get(pk=referencia.pk)
        objeto_id = getattr(antiga, f"{fk}_id")

        _rejeitar_requests_em_andamento(antiga.integration)
        _rejeitar_requests_em_andamento(nova_integracao)

        if classe.objects.filter(
            integration=nova_integracao, external_id=antiga.external_id
        ).exclude(pk=antiga.pk).exists():
            raise IntegrationConflict("Referência já existe na nova integração")

        antiga.integration = nova_integracao
        antiga.save(update_fields=["integration", "alterado_em"])

    registrar_evento_auditoria(
        acao="referencia_externa.propriedade_transferida",
        objeto_tipo=f"{classe._meta.app_label}.{classe.__name__}",
        objeto_id=str(antiga.pk),
        origem="portal",
        usuario=usuario,
        motivo=motivo,
        depois={"nova_integracao": str(nova_integracao.public_id)},
    )
    return antiga


def _rejeitar_requests_em_andamento(integration):
    pendentes = RequisicaoIntegracao.objects.filter(
        integration=integration,
        estado=RequisicaoIntegracao.Estado.EM_PROCESSAMENTO,
    ).exists()
    if pendentes:
        raise IntegrationConflict(
            "Conclua as requisições em processamento antes de transferir a propriedade."
        )
