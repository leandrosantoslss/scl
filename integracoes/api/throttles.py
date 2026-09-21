from django.conf import settings

from integracoes.api.authentication import _ip_do_request
from portal.rate_limit import consume_rate_limit


def _parse_rate(value):
    """Converte '300/min' → (300, 60)."""
    if isinstance(value, int):
        return value, 60
    texto = str(value).strip()
    numero, _, janela = texto.partition("/")
    limite = int(numero)
    janelas = {
        "s": 1,
        "min": 60,
        "m": 60,
        "h": 3600,
        "day": 86400,
        "d": 86400,
    }
    return limite, janelas.get(janela.strip(), 60)


def consumir_origem(request):
    """Limite por origem aplicado ANTES da autenticação."""
    rate = getattr(settings, "SCL_INTEGRATION_ORIGIN_RATE", "300/min")
    limite, janela = _parse_rate(rate)
    ip = _ip_do_request(request)
    return consume_rate_limit("integration:origin", ip, limit=limite, window_seconds=janela)


def consumir_integracao(integration):
    """Limite por integração (limite_requisicoes/min) pós-autenticação."""
    limite = max(1, min(10000, int(integration.limite_requisicoes)))
    return consume_rate_limit(
        "integration",
        integration.public_id,
        limit=limite,
        window_seconds=60,
    )
