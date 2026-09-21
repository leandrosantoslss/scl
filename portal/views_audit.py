from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from portal.models import EventoAuditoria
from portal.roles import ADMINISTRADOR, CADASTRO, CONSULTA, FINANCEIRO


CADASTRO_TIPOS = ["licencas.Cliente", "licencas.Sistema", "licencas.ClienteSistema"]


def auditoria_para_usuario(user):
    queryset = EventoAuditoria.objects.all()

    if user.is_superuser or user.groups.filter(name=ADMINISTRADOR).exists():
        return queryset

    if user.groups.filter(name=CADASTRO).exists() and not user.groups.filter(
        name__in=[FINANCEIRO, CONSULTA]
    ).exists():
        return queryset.filter(objeto_tipo__in=CADASTRO_TIPOS)

    if user.groups.filter(name__in=[FINANCEIRO, CONSULTA]).exists():
        return queryset

    raise PermissionDenied


@login_required
def audit_list(request):
    eventos = auditoria_para_usuario(request.user)
    paginator = Paginator(eventos, 25)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "portal/audit/list.html", {"page": page})


@login_required
def audit_detail(request, public_id):
    eventos = auditoria_para_usuario(request.user)
    evento = get_object_or_404(eventos, public_id=public_id)
    return render(request, "portal/audit/detail.html", {"evento": evento})

