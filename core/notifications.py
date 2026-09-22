from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from portal.models import Notificacao


DEDUPE_JANELA = timedelta(minutes=10)


def notify_users(titulo, mensagem, url=""):
    """Notifica todos os usuários ativos; dedupe por título+mensagem+url na janela."""
    agora = timezone.now()
    limite = agora - DEDUPE_JANELA
    for user in get_user_model()._default_manager.filter(is_active=True).only("id"):
        recente = Notificacao.objects.filter(
            usuario=user,
            titulo=titulo,
            mensagem=mensagem,
            url=url,
            criada_em__gte=limite,
        ).exists()
        if recente:
            continue
        Notificacao.objects.create(
            usuario=user, titulo=titulo, mensagem=mensagem, url=url
        )


def user_notifications(user):
    return list(Notificacao.objects.filter(usuario=user)[:20])


def count_unread(user):
    return Notificacao.objects.filter(usuario=user, lida=False).count()


def mark_notification_read(user, notification_id):
    Notificacao.objects.filter(pk=notification_id, usuario=user).update(lida=True)


def mark_all_notifications_read(user):
    Notificacao.objects.filter(usuario=user, lida=False).update(lida=True)


def delete_all_notifications(user):
    Notificacao.objects.filter(usuario=user).delete()
