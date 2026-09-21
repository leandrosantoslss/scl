from django.db import transaction

from integracoes.models import AssinaturaOrigemCobranca
from portal.audit import registrar_evento_auditoria


def billing_is_external(assinatura) -> bool:
    return hasattr(assinatura, "origem_cobranca")


def trocar_origem_cobranca(assinatura, *, integracao, usuario, motivo):
    """Troca a origem geradora de cobranças de uma assinatura.

    - Motivo é obrigatório.
    - Rejeita requisições legadas em processamento.
    - Competências existentes continuam idempotentes; o gerador interno
      passa a ignorar a assinatura enquanto a origem estiver no legado.
    """
    if not (motivo or "").strip():
        raise ValueError("motivo é obrigatório para trocar a origem de cobrança")

    from integracoes.services.references import _rejeitar_requests_em_andamento

    with transaction.atomic():
        _rejeitar_requests_em_andamento(integracao)

        origem, _criada = AssinaturaOrigemCobranca.objects.get_or_create(
            assinatura=assinatura, defaults={"integracao": integracao}
        )
        origem.integracao = integracao
        origem.save()

        registrar_evento_auditoria(
            acao="assinatura.origem_cobranca.trocada",
            objeto_tipo="licencas.ClienteSistema",
            objeto_id=assinatura.pk,
            origem="portal",
            usuario=usuario,
            motivo=motivo,
            depois={"integracao": str(integracao.public_id)},
        )
    return origem
