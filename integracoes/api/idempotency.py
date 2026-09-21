import hashlib
import json

from django.db import transaction

from integracoes.api.exceptions import EnvelopeError
from integracoes.models import RequisicaoIntegracao


def _canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _payload_hash(request):
    body_bytes = request.body or b""
    try:
        payload = json.loads(body_bytes.decode() or "{}")
    except Exception:
        payload = {}
    digest = hashlib.sha256()
    digest.update(request.method.encode())
    digest.update(request.path.encode())
    digest.update(_canonical(payload).encode())
    return digest.hexdigest()


def _ip_de(request):
    from integracoes.api.authentication import _ip_do_request

    return _ip_do_request(request)


def idempotent_mutation(request, integration, handler):
    """Abre uma mutação idempotente persistida com a chave do header.

    - Mesma chave + mesmo hash: replay da resposta armazenada.
    - Mesma chave + hash diferente: 409 IDEMPOTENCY_CONFLICT.
    - Mesma chave em processamento: 409 REQUEST_IN_PROGRESS.
    - A auditoria de conclusão acontece com a mutação na mesma transação.
    """
    chave = request.headers.get("Idempotency-Key", "")
    if not chave:
        raise EnvelopeError(
            400, "idempotency_key_missing", "Header Idempotency-Key é obrigatório."
        )

    hash_payload = _payload_hash(request)

    with transaction.atomic():
        requisicao, criada = RequisicaoIntegracao.objects.get_or_create(
            integration=integration,
            chave_idempotencia=chave,
            defaults={
                "request_id": chave[:64],
                "metodo": request.method,
                "endpoint": request.path,
                "payload_hash": hash_payload,
                "estado": RequisicaoIntegracao.Estado.EM_PROCESSAMENTO,
                "ip": _ip_de(request),
            },
        )

        if not criada:
            if requisicao.estado == RequisicaoIntegracao.Estado.EM_PROCESSAMENTO:
                raise EnvelopeError(
                    409, "REQUEST_IN_PROGRESS", "Requisição equivalente em processamento."
                )
            if requisicao.payload_hash != hash_payload:
                raise EnvelopeError(
                    409, "IDEMPOTENCY_CONFLICT", "Mesma chave com payload diferente."
                )
            return {
                "replayed": True,
                "http_status": requisicao.http_status,
                "payload": requisicao.resposta_snapshot,
            }, requisicao

        resultado = handler(request, requisicao)
        if isinstance(resultado, dict) and {"http_status", "payload"}.issubset(resultado):
            requisicao.http_status = resultado["http_status"]
            requisicao.resposta_snapshot = resultado["payload"]
        requisicao.estado = RequisicaoIntegracao.Estado.CONCLUIDA
        requisicao.concluida_em = timezone_now_utc()
        requisicao.save()
        return resultado, requisicao


def timezone_now_utc():
    from django.utils import timezone

    return timezone.now()
