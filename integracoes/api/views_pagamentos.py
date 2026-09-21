import json

from django.core.exceptions import ValidationError

from financeiro.models import Cobranca, Pagamento
from financeiro.selectors import saldo_cobranca
from financeiro.services.pagamentos import _atualizar_status_cobranca
from integracoes.api.exceptions import EnvelopeError
from integracoes.api.idempotency import idempotent_mutation
from integracoes.api.permissions import exigir_escopo
from integracoes.api.views_base import IntegrationAPIView, resposta_json
from integracoes.api.views_financeiro import (
    _assinatura,
    _assinatura_por_external_id,
    _json,
)
from integracoes.api.serializers_assinaturas import serializar_assinatura
from integracoes.models import (
    CobrancaReferenciaExterna,
    PagamentoReferenciaExterna,
)
from integracoes.services import financeiro as services_financeiro


class PagamentosCreateListView(IntegrationAPIView):
    def processar(self, request, cobranca_external_id=None, **kwargs):
        if request.method == "GET":
            exigir_escopo(request.integration_token, "finance:read")
            return self._listar(request)
        exigir_escopo(request.integration_token, "payments:write")
        return self._criar(request)

    def _listar(self, request):
        integration = request.integration
        query = Pagamento.objects.filter(integration=integration).order_by("pk")
        cursor = request.GET.get("cursor")
        if cursor:
            query = query.filter(pk__gt=int(cursor))
        state = request.GET.get("state", "")
        if state == "confirmed":
            query = query.filter(status=Pagamento.Status.CONFIRMED)
        elif state == "reversed":
            query = query.filter(status=Pagamento.Status.REVERSED)
        external_id = request.GET.get("external_id", "")
        if external_id:
            pks = PagamentoReferenciaExterna.objects.filter(
                integration=integration, external_id=external_id
            ).values_list("pagamento_id", flat=True)
            query = query.filter(pk__in=list(pks))
        if updated_since := request.GET.get("updated_since", ""):
            query = query.filter(alterado_em__gte=updated_since)
        pagina = list(query[:50])
        referencias = {
            r.pagamento_id: r.external_id
            for r in PagamentoReferenciaExterna.objects.filter(
                integration=integration, pagamento_id__in=[p.pk for p in pagina]
            )
        }
        from integracoes.api.serializers_financeiro import serializar_pagamento

        return resposta_json(
            {
                "items": [
                    serializar_pagamento(p, external_id=referencias.get(p.pk))
                    for p in pagina
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
        cobranca_eid = payload.get("cobranca_external_id", "")
        if not cobranca_eid:
            raise EnvelopeError(
                400, "cobranca_external_id_missing", "cobranca_external_id é obrigatório."
            )

        def handler(req, _r):
            try:
                ref, cobranca = _cobranca_por_external_id(req.integration, cobranca_eid)
                pagamento = services_financeiro.registrar_pagamento_legado(
                    cobranca=cobranca,
                    payload=payload,
                    integration=req.integration,
                )
            except ValidationError as erro:
                raise EnvelopeError(400, "invalid_payload", str(erro.messages[0]))
            from integracoes.api.serializers_financeiro import serializar_pagamento

            return {
                "http_status": 201,
                "payload": serializar_pagamento(pagamento, external_id=external_id),
            }

        result, _ = idempotent_mutation(request, request.integration, handler)
        status = result.get("http_status", 201)
        return resposta_json(result.get("payload"), status=status)


class PagamentoEstornoView(IntegrationAPIView):
    def processar(self, request, external_id, **kwargs):
        exigir_escopo(request.integration_token, "payments:reverse")
        payload = _json(request)

        def handler(req, _r):
            ref = PagamentoReferenciaExterna.objects.filter(
                integration=req.integration, external_id=external_id
            ).first()
            if ref is None:
                raise EnvelopeError(404, "not_found", "Pagamento externo não encontrado.")
            try:
                estornado = services_financeiro.estornar_pagamento_legado(
                    pagamento=ref.pagamento,
                    motivo=payload.get("motivo", ""),
                    integration=req.integration,
                )
            except ValidationError as erro:
                raise EnvelopeError(403, "reversal_not_allowed", erro.messages[0])
            from integracoes.api.serializers_financeiro import serializar_pagamento

            return {"http_status": 200, "payload": serializar_pagamento(estornado, external_id=external_id)}

        result, _ = idempotent_mutation(request, request.integration, handler)
        if result.get("replayed"):
            return resposta_json(result.get("payload"), status=result.get("http_status") or 200)
        return resposta_json(result.get("payload"), status=result.get("http_status", 200))


class CobrancaCancelarView(IntegrationAPIView):
    def processar(self, request, external_id):
        exigir_escopo(request.integration_token, "finance:write")
        return self._cancelar(request, external_id)

    def _cancelar(self, request, external_id):
        payload = _json(request)

        def handler(req, _r):
            ref = CobrancaReferenciaExterna.objects.filter(
                integration=req.integration, external_id=external_id
            ).first()
            if ref is None:
                raise EnvelopeError(404, "not_found", "Cobrança externa não encontrada.")
            try:
                cancelada = services_financeiro.cancelar_cobranca_legado(
                    cobranca=ref.cobranca, integration=req.integration, motivo=payload.get("motivo", "")
                )
            except ValidationError as erro:
                raise EnvelopeError(400, "reversal_not_allowed", erro.messages[0])
            from integracoes.api.serializers_financeiro import serializar_cobranca

            return {"http_status": 200, "payload": serializar_cobranca(cancelada, external_id=external_id)}

        result, _ = idempotent_mutation(request, request.integration, handler)
        if result.get("replayed"):
            return resposta_json(result.get("payload"), status=result.get("http_status") or 200)
        return resposta_json(result.get("payload"), status=result.get("http_status", 200))


class ChargesDetalheCancelarView(IntegrationAPIView):
    """GET lista/detalhes da cobrança; PATCH cancela (origem legada)."""

    def processar(self, request, external_id, **kwargs):
        if request.method == "GET":
            exigir_escopo(request.integration_token, "finance:read")
            ref = CobrancaReferenciaExterna.objects.filter(
                integration=request.integration, external_id=external_id
            ).first()
            if ref is None:
                raise EnvelopeError(404, "not_found", "Cobrança externa não encontrada.")
            from integracoes.api.serializers_financeiro import serializar_cobranca

            cobranca = Cobranca.objects.get(pk=ref.cobranca_id)
            return resposta_json(serializar_cobranca(cobranca, external_id=external_id))

        exigir_escopo(request.integration_token, "finance:write")
        payload = _json(request)
        return self._cancelar(request, external_id)


def _cobranca_por_external_id(integration, cobranca_eid):
    ref = CobrancaReferenciaExterna.objects.filter(
        integration=integration, external_id=cobranca_eid
    ).first()
    if ref is None:
        raise EnvelopeError(404, "not_found", "Cobrança externa não encontrada.")
    return ref, Cobranca.objects.select_for_update().get(pk=ref.cobranca_id)
