from datetime import datetime, timedelta, timezone as _dt_tz

from django.db import transaction
from django.utils import timezone

from portal.models import JanelaRateLimit


def _janela_inicio(window_start_seconds):
    now = timezone.now()
    epoch = int(now.timestamp())
    window = int(window_start_seconds)
    start_epoch = epoch - (epoch % window)
    return datetime.fromtimestamp(start_epoch, _dt_tz.utc)


def consume_rate_limit(scope, key, *, limit, window_seconds):
    """Consome uma unidade do bucket atômico.

    - Incremento com lock de linha (row lock).
    - Bucket remove-se com delete oportunista (1% das chamadas).
    """
    window_start = _janela_inicio(window_seconds)
    key_hash = _hash_key(key)

    with transaction.atomic():
        row, _criada = JanelaRateLimit.objects.get_or_create(
            scope=scope,
            key_hash=key_hash,
            window_start=window_start,
            defaults={"contagem": 0},
        )
        row = JanelaRateLimit.objects.select_for_update().get(pk=row.pk)
        if row.contagem + 1 > limit:
            return False
        row.contagem += 1
        row.save(update_fields=["contagem"])

    if timezone.now().microsecond % 100 == 0:
        _limpar_expiradas(window_seconds)
    return True


def _limpar_expiradas(window_seconds):
    limite = timezone.now() - timedelta(seconds=window_seconds * 2)
    JanelaRateLimit.objects.filter(window_start__lt=limite).delete()


def _hash_key(value):
    import hashlib

    return hashlib.sha256(str(value).encode()).hexdigest()
