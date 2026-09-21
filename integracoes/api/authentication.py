from django.utils import timezone
from oauth2_provider.models import AccessToken

from integracoes.api.exceptions import EnvelopeError
from integracoes.models import IntegracaoLegado


def _ip_do_request(request):
    """Deriva o IP respeitando SCL_TRUSTED_PROXY_CIDRS."""
    from django.conf import settings
    import ipaddress

    remote = request.META.get("REMOTE_ADDR", "")
    proxies = getattr(settings, "SCL_TRUSTED_PROXY_CIDRS", [])
    if proxies:
        try:
            remote_ip = ipaddress.ip_address(remote)
        except ValueError:
            remote_ip = None
        if remote_ip and any(
            remote_ip in ipaddress.ip_network(cidr, strict=False) for cidr in proxies
        ):
            forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
            return forwarded.split(",")[0].strip() or remote
    return remote


def integracao_do_request(request):
    """Resolve a integração a partir de `Authorization: Bearer <token>`."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer ") or len(header.split(" ", 1)) < 2:
        raise EnvelopeError(401, "missing_or_invalid_token", "Token ausente ou inválido.")

    token_valor = header.split(" ", 1)[1]
    try:
        token = AccessToken.objects.get(token=token_valor)
    except AccessToken.DoesNotExist:
        raise EnvelopeError(401, "missing_or_invalid_token", "Token ausente ou inválido.")

    if token.expires and token.expires <= timezone.now():
        raise EnvelopeError(401, "missing_or_invalid_token", "Token ausente ou inválido.")

    try:
        integration = token.application.integracao_legado
    except IntegracaoLegado.DoesNotExist:
        raise EnvelopeError(401, "missing_or_invalid_token", "Token ausente ou inválido.")

    if not integration.ativo:
        raise EnvelopeError(401, "missing_or_invalid_token", "Token ausente ou inválido.")
    if integration.credencial_expira_em and integration.credencial_expira_em <= timezone.now():
        raise EnvelopeError(401, "missing_or_invalid_token", "Token ausente ou inválido.")

    return integration, token
