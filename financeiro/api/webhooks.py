from django.http import JsonResponse

from financeiro.gateways.registry import get_adapter
from financeiro.models import ContaGateway
from financeiro.services import webhooks


def processar_webhook(request, provedor, conta_public_id, **kwargs):
    account = ContaGateway.objects.filter(public_id=conta_public_id, provedor=provedor).first()
    if account is None:
        return JsonResponse({"code": "not_found"}, status=404)
    adaptador = get_adapter(account)
    corpo_bytes = request.body
    try:
        evento = adaptador.parse_webhook(headers=dict(request.headers), body=corpo_bytes)
    except Exception as erro:
        import logging

        logging.getLogger("django.request").error(
            "webhook rejected: provider signature failed", exc_info=erro
        )
        return JsonResponse({"code": "invalid"}, status=401)

    evento, duplicado = webhooks.processar_evento_gateway(account, evento)
    return JsonResponse(
        {
            "evento": evento.id_evento_externo,
            "status": evento.get_status_display(),
            "duplicado": duplicado,
        },
        status=200,
    )
