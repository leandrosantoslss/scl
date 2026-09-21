import base64
import ipaddress

from django.utils import timezone
from oauth2_provider.models import Application
from oauth2_provider.views import TokenView

from integracoes.models import IntegracaoLegado


def _origem_confere(ip_candidato, redes_permitidas):
    """CIDRs vazios permitem tudo."""
    if not redes_permitidas:
        return True
    try:
        remote = ipaddress.ip_address(ip_candidato)
    except ValueError:
        return False
    for rede in redes_permitidas:
        try:
            if remote in ipaddress.ip_network(rede, strict=False):
                return True
        except ValueError:
            continue
    return False


class IntegrationTokenView(TokenView):
    """Endpoint de token com regras da integração (ativo/credencial/rede)."""

    def _credenciais_basic(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.lower().startswith("basic "):
            return None
        try:
            decoded = base64.b64decode(header.split(" ", 1)[1]).decode()
            client_id, _, client_secret = decoded.partition(":")
        except Exception:
            return None
        return client_id, client_secret

    def post(self, request, *args, **kwargs):
        credenciais = self._credenciais_basic(request)
        if credenciais is None:
            response = super().post(request, *args, **kwargs)
            return response

        client_id, _secret = credenciais
        try:
            application = Application.objects.get(client_id=client_id)
        except Application.DoesNotExist:
            return super().post(request, *args, **kwargs)

        try:
            integration = application.integracao_legado
        except IntegracaoLegado.DoesNotExist:
            return super().post(request, *args, **kwargs)

        if not integration.ativo:
            return _resposta_padronizada(403, "integration_inactive")

        if integration.credencial_expira_em and integration.credencial_expira_em <= timezone.now():
            return _resposta_padronizada(403, "integration_expired")

        if not _origem_confere(request.META.get("REMOTE_ADDR", ""), integration.redes_permitidas):
            return _resposta_padronizada(403, "origin_not_allowed")

        escopos_solicitados = request.POST.get("scope", "").split()
        if escopos_solicitados:
            permitidos = set(integration.escopos or [])
            if not permitidos or not set(escopos_solicitados).issubset(permitidos):
                return _resposta_padronizada(403, "scope_not_authorized")

        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            integracao_refresh = IntegracaoLegado.objects.get(pk=integration.pk)
            integracao_refresh.ultimo_uso_em = timezone.now()
            integracao_refresh.save(update_fields=["ultimo_uso_em"])

        return response


def _resposta_padronizada(status, code):
    from django.http import JsonResponse

    messages = {
        "integration_inactive": "Integração inativa.",
        "integration_expired": "Credencial expirada.",
        "origin_not_allowed": "Origem não autorizada.",
    }
    return JsonResponse(
        {"code": code, "message": messages.get(code, "Falha de autorização.")},
        status=status,
    )
