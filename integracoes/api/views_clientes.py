import json

from django.db import IntegrityError, transaction

from integracoes.api.exceptions import EnvelopeError
from integracoes.api.idempotency import idempotent_mutation
from integracoes.api.permissions import exigir_escopo
from integracoes.api.views_base import IntegrationAPIView, resposta_json
from integracoes.api.serializers_clientes import serializar_cliente
from integracoes.models import ClienteReferenciaExterna, Recurso
from integracoes.services import policies, references
from integracoes.services.clientes import atualizar_cliente_api, criar_cliente_api
from licencas.models import Cliente
from licencas.validators import normalize_document


def _dados_do_payload(payload):
    """Explicit allowlist dos campos do domínio de cliente."""
    permitidos = {
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
        "ativo",
        "bloqueado",
        "motivo_bloqueio",
    }
    return {key: value for key, value in payload.items() if key in permitidos}


class ClienteListCreateView(IntegrationAPIView):
    def processar(self, request):
        if request.method == "GET":
            exigir_escopo(request.integration_token, "clients:read")
            return self._listar(request)
        exigir_escopo(request.integration_token, "clients:write")
        return self._criar(request)

    def _listar(self, request):
        integration = request.integration
        queryset = Cliente.objects.order_by("pk")

        cursor = request.GET.get("cursor")
        if cursor:
            queryset = queryset.filter(pk__gt=int(cursor))
        if external_id := request.GET.get("external_id", ""):
            pks = ClienteReferenciaExterna.objects.filter(
                integration=integration, external_id=external_id
            ).values_list("cliente_id", flat=True)
            queryset = queryset.filter(pk__in=list(pks))
        if document := request.GET.get("document", ""):
            queryset = queryset.filter(cnpjcpf__icontains=normalize_document(document))
        state = request.GET.get("state", "")
        if state == "active":
            queryset = queryset.filter(ativo=True, bloqueado=False)
        elif state == "inactive":
            queryset = queryset.filter(ativo=False)
        elif state == "blocked":
            queryset = queryset.filter(bloqueado=True)
        if updated_since := request.GET.get("updated_since", ""):
            queryset = queryset.filter(alterado_em__gte=updated_since)

        pagina = list(queryset[:50])
        referencias = {
            ref.cliente_id: ref.external_id
            for ref in ClienteReferenciaExterna.objects.filter(
                integration=integration, cliente_id__in=[c.pk for c in pagina]
            )
        }
        return resposta_json(
            {
                "items": [
                    serializar_cliente(cliente, external_id=referencias.get(cliente.pk))
                    for cliente in pagina
                ],
                "next_cursor": str(pagina[-1].pk) if len(pagina) == 50 else None,
            }
        )

    def _criar(self, request):
        try:
            payload = json.loads(request.body.decode() or "{}")
        except Exception:
            raise EnvelopeError(400, "invalid_payload", "Payload inválido.")

        politica = policies._politica(request.integration, resource=Recurso.CLIENTE)
        if politica is None:
            raise EnvelopeError(403, "policy_missing", "Sem política para clients nesta integração.")
        if politica.modo == "scl_master":
            raise EnvelopeError(
                403,
                "scl_master_rejects_external_write",
                "Escrita externa bloqueada: resource é SCL_MASTER.",
            )

        external_id = payload.pop("external_id", "")
        if not external_id:
            raise EnvelopeError(400, "external_id_missing", "external_id é obrigatório.")

        def handler(req, _requisicao):
            try:
                cliente = criar_cliente_api(
                    _dados_do_payload(payload),
                    req.integration,
                    external_id,
                    usuario=None,
                )
            except (IntegrityError, Exception):  #	IntegrityError + ValidationError/400
                raise EnvelopeError(
                    409,
                    "external_id_conflict",
                    "external_id/documento já existe nesta integração.",
                )
            return {
                "http_status": 201,
                "payload": serializar_cliente(cliente, external_id=external_id),
            }

        resultado, _ = idempotent_mutation(request, request.integration, handler)
        if isinstance(resultado, dict) and resultado.get("replayed") is True:
            return resposta_json(resultado["payload"], status=resultado["http_status"])
        return resposta_json(resultado["payload"], status=resultado["http_status"])


class ClienteDetailView(IntegrationAPIView):
    def processar(self, request, external_id):
        if request.method == "GET":
            exigir_escopo(request.integration_token, "clients:read")
            return self._detalhar(request, external_id)
        exigir_escopo(request.integration_token, "clients:write")
        return self._atualizar(request, external_id)

    def _detalhar(self, request, external_id):
        referencia, cliente = references.resolve_external_reference(
            Cliente, request.integration, external_id
        )
        if referencia is None:
            raise EnvelopeError(404, "not_found", "Referência externa não encontrada.")
        return resposta_json(serializar_cliente(cliente, external_id=external_id))

    def _atualizar(self, request, external_id):
        referencia, cliente = references.resolve_external_reference(
            Cliente, request.integration, external_id
        )
        if referencia is None:
            raise EnvelopeError(404, "not_found", "Referência externa não encontrada.")
        try:
            payload = json.loads(request.body.decode() or "{}")
        except Exception:
            raise EnvelopeError(400, "invalid_payload", "Payload inválido.")

        politica = policies._politica(request.integration, resource=Recurso.CLIENTE)
        if politica is None:
            raise EnvelopeError(403, "policy_missing", "Sem política para clients nesta integração.")
        if politica.modo == "scl_master":
            raise EnvelopeError(
                403,
                "scl_master_rejects_external_write",
                "Escrita externa bloqueada: resource é SCL_MASTER.",
            )
        if politica.modo == "shared":
            from integracoes.api.etag import check_if_match

            check_if_match(request, cliente)

        def handler(req, _requisicao):
            try:
                atualizado = atualizar_cliente_api(
                    cliente,
                    _dados_do_payload(payload),
                    req.integration,
                    external_id,
                    usuario=None,
                )
                return {
                    "http_status": 200,
                    "payload": serializar_cliente(atualizado, external_id=external_id),
                }
            except IntegrityError:
                raise EnvelopeError(409, "external_id_conflict", "Documento duplicado na integração.")

        resultado, _ = idempotent_mutation(request, request.integration, handler)
        if isinstance(resultado, dict) and resultado.get("replayed") is True:
            return resposta_json(resultado["payload"], status=resultado["http_status"])
        return resposta_json(resultado["payload"], status=resultado["http_status"])


class ClienteBatchUpsertView(IntegrationAPIView):
    def processar(self, request):
        exigir_escopo(request.integration_token, "clients:write")
        try:
            envelope = json.loads(request.body.decode() or "{}")
        except Exception:
            raise EnvelopeError(400, "invalid_payload", "Payload de lote inválido.")

        itens = envelope.get("items", [])
        if not isinstance(itens, list) or len(itens) > 100:
            raise EnvelopeError(400, "batch_limit_exceeded", "Lote aceita no máximo 100 itens.")

        aceitos = 0
        rejeitados = 0
        resultados = []
        integration = request.integration

        for item in itens:
            try:
                external_id = item.get("external_id", "")
                if not external_id:
                    raise EnvelopeError(400, "external_id_missing", "external_id obrigatório por item.")
                with transaction.atomic():
                    referencia, cliente = references.resolve_external_reference(
                        Cliente, integration, external_id
                    )
                    dados = _dados_do_payload(item)
                    if cliente is None:
                        cliente = criar_cliente_api(dados, integration, external_id, usuario=None)
                        estados = "created"
                    else:
                        cliente = atualizar_cliente_api(
                            cliente, dados, integration, external_id, usuario=None
                        )
                        estados = "updated"
                    aceitos += 1
                    resultados.append(
                        {
                            "external_id": external_id,
                            "resultado": estados,
                        }
                    )
            except Exception as erro:
                rejeitados += 1
                resultados.append(
                    {
                        "external_id": item.get("external_id"),
                        "resultado": "rejected",
                        "code": "validation_error",
                        "message": str(erro),
                    }
                )

        return resposta_json(
            {
                "recebidos": len(itens),
                "aceitos": aceitos,
                "rejeitados": rejeitados,
                "itens": resultados,
            }
        )
