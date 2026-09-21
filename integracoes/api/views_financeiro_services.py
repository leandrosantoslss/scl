from django.db import transaction

from integracoes.api.exceptions import EnvelopeError
from integracoes.api.permissions import exigir_escopo
from integracoes.api.views_base import IntegrationAPIView, resposta_json
from integracoes.api.serializers_assinaturas import serializar_assinatura
from integracoes.models import AssinaturaReferenciaExterna, Recurso
from integracoes.services import policies, references
from licencas.models import Cliente, ClienteSistema


ASSINATURA_CAMPOS = (
    "valor_recorrente",
    "periodicidade",
    "data_inicio",
    "data_fim",
    "primeiro_vencimento",
    "dia_vencimento",
    "dias_carencia",
    "ativo",
    "bloqueado",
    "motivo_bloqueio",
)


class AssinaturasListCreateView(IntegrationAPIView):
    escape = ("subscriptions:read", "subscriptions:write")

    def processar(self, request):
        if request.method == "GET":
            exigir_escopo(request.integration_token, "subscriptions:read")
            return self._listar(request)
        exigir_escopo(request.integration_token, "subscriptions:write")
        return self._criar(request)

    def _listar(self, request):
        integration = request.integration
        queryset = ClienteSistema.objects.order_by("pk")

        cursor = request.GET.get("cursor")
        if cursor:
            queryset = queryset.filter(pk__gt=int(cursor))

        external_id = request.GET.get("external_id", "")
        if external_id:
            pks = AssinaturaReferenciaExterna.objects.filter(
                integration=integration, external_id=external_id
            ).values_list("assinatura_id", flat=True)
            queryset = queryset.filter(pk__in=list(pks))

        state = request.GET.get("state", "")
        if state == "active":
            queryset = queryset.filter(ativo=True, bloqueado=False)
        elif state == "inactive":
            queryset = queryset.filter(ativo=False)
        elif state == "blocked":
            queryset = queryset.filter(bloqueado=True)

        updated_since = request.GET.get("updated_since", "")
        if updated_since:
            queryset = queryset.filter(alterado_em__gte=updated_since)

        pagina = list(queryset[:50])
        referencia_map = {
            ref.assinatura_id: ref.external_id
            for ref in AssinaturaReferenciaExterna.objects.filter(
                integration=integration, assinatura_id__in=[a.pk for a in pagina]
            )
        }
        return resposta_json(
            {
                "items": [
                    serializar_assinatura(assinatura, external_id=referencia_map.get(assinatura.pk))
                    for assinatura in pagina
                ],
                "next_cursor": str(pagina[-1].pk) if len(pagina) == 50 else None,
            }
        )

    def _criar(self, request):
        import json

        try:
            payload = json.loads(request.body.decode() or "{}")
        except Exception:
            raise EnvelopeError(400, "invalid_payload", "Payload inválido.")

        external_id = payload.get("external_id", "")
        if not external_id:
            raise EnvelopeError(400, "external_id_missing", "external_id é obrigatório.")
        cliente_external_id = payload.get("cliente_external_id")
        if not cliente_external_id:
            raise EnvelopeError(
                400, "cliente_external_id_missing", "cliente_external_id é obrigatório."
            )

        def handler(req, requisicao):
            try:
                assinatura = criar_assinatura_api(payload, req.integration, external_id)
                return {
                    "http_status": 201,
                    "payload": serializar_assinatura(assinatura, external_id=external_id),
                }
            except IntegrityError:
                raise EnvelopeError(409, "external_id_conflict", "Identidade externa duplicada")

        resultado, _requisicao = idempotent_mutation(request, req_or_none_integration(request, req_something()), handler)
        return resposta_json(
            resultado["payload"],
            status=resultado.get("http_status", 201),
        )


def req_or_none_integration(request, req):
    pass


def criar_assinatura_api(dados, integration, external_id, usuario):
    from licencas.services import assinaturas as assinatura_services
    from licencas.models import Sistema

    cliente_external_id = dados.get("cliente_external_id")
    sistema_codigo = dados.pop("sistema_codigo", "default")

    with transaction.atomic():
        cliente_legado, cliente = references.resolve_external_reference(
            Cliente, integration, cliente_external_id
        )
        sistema, _criado = ClienteSistema._meta.get_field("sistema").remote_field.model.objects.get_or_create(
            nome=sistema_codigo, codigo=sistema_codigo
        )
        assinatura, criada = ClienteSistema.objects.get_or_create(
            cliente=cliente,
            sistema=sistema,
            defaults={campo: dados.get(campo) for campo in ASSINATURA_CAMPOS},
        )
        if criada:
            from portal.audit import registrar_evento_auditoria

            registrar_evento_auditoria(
                acao="assinatura.criada",
                objeto_tipo="licencas.ClienteSistema",
                objeto_id=assinatura.pk,
                origem="integration",
                usuario=usuario,
            )
            if assinatura.ativo:
                assinatura.full_clean()
                assinatura.save()
        references.obter_ou_criar_referencia(
            ClienteSistema, integration=integration, external_id=external_id, objeto=assinatura
        )
    return assinatura


from licencas.models import ClienteSistema
