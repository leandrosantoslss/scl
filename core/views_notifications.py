from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.notifications import (
    count_unread,
    delete_all_notifications,
    mark_all_notifications_read,
    mark_notification_read,
    user_notifications,
)


def _serializar(notificacao):
    return {
        "id": notificacao.pk,
        "titulo": notificacao.titulo,
        "mensagem": notificacao.mensagem[:140],
        "url": notificacao.url or (reverse("portal:home") if False else ""),
        "lida": notificacao.lida,
        "criada_em": notificacao.criada_em.isoformat(),
    }


@login_required
def notifications_api(request):
    itens = [_serializar(n) for n in user_notifications(request.user)]
    return JsonResponse(
        {"count": count_unread(request.user), "items": itens}
    )


@require_POST
@login_required
def notification_read_api(request, pk):
    mark_notification_read(request.user, notification_id=pk)
    return JsonResponse({"ok": True, "unread": count_unread(request.user)})


@require_POST
@login_required
def notifications_read_all_api(request):
    mark_all_notifications_read(request.user)
    return JsonResponse({"ok": True, "unread": count_unread(request.user)})


@require_POST
@login_required
def notifications_delete_all_api(request):
    delete_all_notifications(request.user)
    return JsonResponse({"ok": True, "unread": 0})
