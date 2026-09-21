import time

from django.http import JsonResponse
from integracoes.api.views_base import IntegrationAPIView


class EchoView(IntegrationAPIView):
    """Rota de infraestrutura usada para validar auth/CIDR/rate limit."""

    def processar(self, request, *args, **kwargs):
        return JsonResponse(
            {
                "echo": request.method,
                "integration": (
                    str(request.integration.public_id)
                    if hasattr(request, "integration")
                    else None
                ),
                "ts": round(time.time(), 3),
            }
        )


def adaptar_para_urls(classe_view):
    """Adaptador de classes `IntegrationAPIView` (não-View) para URLs Django."""

    def view(request, *args, **kwargs):
        return classe_view().dispatch(request, *args, **kwargs)

    return view


echo_status = adaptar_para_urls(EchoView)
