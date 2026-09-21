import logging

from django.conf import settings
from django.http import JsonResponse
from integracoes.api.exceptions import EnvelopeError

import ipaddress


def _erro(status, code, mensagem, details=None):
    payload = {"code": code, "message": mensagem}
    if details is not None:
        payload["details"] = details
    return JsonResponse(payload, status=status)


def resposta_json(content, *, status=200, headers=None):
    response = JsonResponse(content, status=status)
    for key, value in (headers or {}).items():
        response[key] = value
    return response


def _origem_permitida(request, integration):
    """CIDRs da integração; vazio permite qualquer origem."""
    permitir = integration.redes_permitidas or []
    if not permitir:
        return True
    from integracoes.api.authentication import _ip_do_request

    try:
        remote = ipaddress.ip_address(_ip_do_request(request))
    except ValueError:
        return False
    for rede in permitir:
        try:
            if remote in ipaddress.ip_network(rede, strict=False):
                return True
        except ValueError:
            continue
    return False


class IntegrationAPIView:
    """Base das views administrativas:

    1. Rate limit por origem ANTES da autenticação.
    2. Autenticação (401 em qualquer falha).
    3. CIDRs da integração revalidados a cada requisição.
    4. Rate limit por integração (req/min pós-auth).
    """

    def dispatch(self, request, *args, **kwargs):
        try:
            return self._pipeline(request, *args, **kwargs)
        except EnvelopeError as erro:
            return _erro(erro.status, erro.code, erro.mensagem, erro.details)
        except Exception as erro:  # noqa: BLE001
            logging.getLogger("django.request").error("integration api error", exc_info=erro)
            return _erro(503, "temporary_unavailable", "Falha temporária; repita depois.")

    def _pipeline(self, request, *args, **kwargs):
        from integracoes.api.authentication import integracao_do_request
        from integracoes.api import throttles

        if not throttles.consumir_origem(request):
            raise EnvelopeError(429, "origin_rate_limited", "Limite por origem atingido.")

        integration, token = integracao_do_request(request)

        if not _origem_permitida(request, integration):
            raise EnvelopeError(403, "origin_not_allowed", "Origem não autorizada.")

        if not throttles.consumir_integracao(integration):
            raise EnvelopeError(
                429,
                "integration_rate_limited",
                "Limite de requisições da integração atingido.",
            )

        request.integration = integration
        request.integration_token = token
        return self._executar(request, *args, **kwargs)

    def _executar(self, request, *args, **kwargs):
        return self.processar(request, *args, **kwargs)

    def processar(self, request, *args, **kwargs):
        raise NotImplementedError
