import json

from django.db import IntegrityError, transaction

from financeiro.models import Cobranca, Pagamento
from financeiro.selectors import saldo_cobranca
from financeiro.services.pagamentos import _atualizar_status_cobranca

from integracoes.api.exceptions import EnvelopeError
from integracoes.api.idempotency import idempotent_mutation
from integracoes.api.permissions import exigir_escopo
from integracoes.api.views_base import IntegrationAPIView, resposta_json
from integracoes.api.serializers_assinaturas import serializar_assinatura

from integracoes.models import (
    AssinaturaReferenciaExterna,
    CobrancaReferenciaExterna,
    PagamentoReferenciaExterna,
)
from integracoes.services import financeiro as services_financeiro
from licencas.models import ClienteSistema
from datetime import datetime


def _dados_cobranca(payload, assinatura):
    return {
        "competencia": payload.get("competencia"),
        "vencimento": payload.get("vencimento"),
        "fim_carencia": payload.get("fim_carencia"),
        "valor_original": payload.get("valor_original"),
        "descricao": payload.get("descricao", ""),
    }


class ChargesCreateListView(IntegrationAPIView):
    """POST cria cobrança (legada) + GET lista com cursor e filtros."""

    def processar(self, request):
        if request.method == "GET":
            exigir_escopo(request.integration_token, "finance:read")
            return self._listar(request)
        exigir_escopo(request.integration_token, "finance:write")
        return self._criar(request)

    def _listar(self, request):
        query = Cobranca.objects.order_by("pk").select_related("assinatura")
        cursor = request.GET.get("cursor")
        if cursor:
            query = query.filter(pk__gt=int(cursor))
        state = request.GET.get("state", "")
        if state == "aberta":
            query = query.filter(status=Cobranca.Status.ABERTA)
        elif state == "paga":
            query = query.filter(status=Cobranca.Status.PAGA)
        elif state == "cancelada":
            query = query.filter(status=Cobranca.Status.CANCELADA)
        external_id = request.GET.get("external_id", "")
        if external_id:
            pks = CobrancaReferenciaExterna.objects.filter(
                integration=request.integration, external_id=external_id
            ).values_list("cobranca_id", flat=True)
            query = query.filter(pk__in=list(pks))
        if updated_since := request.GET.get("updated_since", ""):
            query = query.filter(alterado_em__gte=updated_since)
        if subscription_external_id := request.GET.get("subscription", ""):
            sub_ref, assinatura = _assinatura_por_external_id(request.integration, subscription_external_id)
            if assinatura is not None:
                query = query.filter(assinatura=assinatura)
        pagina = list(query[:50])
        referencias = {r.cobranca_id: r.external_id for r in CobrancaReferenciaExterna.objects.filter(integration=request.integration, cobranca_id__in=[c.pk for c in pagina])}
        return resposta_json(
            {
                "items": [
                    {
                        "external_id": referencias.get(c.pk),
                        "internal_id": c.pk,
                        "competencia": c.competencia.isoformat(),
                        "vencimento": c.vencimento.isoformat(),
                        "fim_carencia": c.fim_carencia.isoformat(),
                        "valor_original": str(c.valor_original),
                        "saldo": str(saldo_cobranca(c)),
                        "status": c.status,
                        "origem": c.origem,
                        "version": _version(c),
                        "updated_at": c.alterado_em.isoformat() if c.alterado_em else None,
                    }
                    for c in pagina
                ],
                "next_cursor": str(pagina[-1].pk) if len(pagina) == 50 else None,
            }
        )

    def _criar(self, request):
        payload = _json(request)
        external_id = payload.get("external_id", "")
        if not external_id:
            raise EnvelopeError(400, "external_id_missing", "external_id é obrigatório.")
        sub_eid = payload.get("subscription_external_id", "")
        if not sub_eid:
            raise EnvelopeError(
                400, "subscription_external_id_missing", "subscription_external_id é obrigatório."
            )

        def handler(req, _r):
            try:
                cobranca = services_financeiro.criar_cobranca_legado(
                    assinatura=_assinatura(req.integration, sub_eid),
                    payload=_dados_cobranca(payload, None) | {"external_id": external_id},
                    integration=req.integration,
                    usuario=None,
                )
            except IntegrityError:
                raise EnvelopeError(
                    409, "external_id_conflict", "Ciclo ou external_id já existem."
                )
            from integracoes.api.serializers_financeiro import serializar_cobranca

            return {
                "http_status": 201,
                "payload": serializar_cobranca(cobranca, external_id=external_id),
            }

        result, _ = idempotent_mutation(request, request.integration, handler)
        status = result.get("http_status") or 201
        return resposta_json(result["payload"], status=status)


def _assinatura(integration, sub_eid):
    _, assinatura = _assinatura_por_external_id(integration, sub_eid)
    return assinatura


def _assinatura_por_external_id(integration, external_id):
    from licencas.models import ClienteSistema

    ref = AssinaturaReferenciaExterna.objects.filter(
        integration=integration, external_id=external_id
    ).first()
    if not ref:
        raise EnvelopeError(404, "not_found", "Assinatura externa não encontrada.")
    return ref, ClienteSistema.objects.get(pk=ref.assinatura_id)


def _assinatura_via(id):
    return None


def _json(request):
    try:
        return json.loads(request.body.decode() or "{}")
    except Exception:
        raise EnvelopeError(400, "invalid_payload", "Payload inválido.")


def _version(obj):
    from integracoes.api.etag import version_for

    return version_for(obj)
