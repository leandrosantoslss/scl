import secrets

from django.contrib.auth.decorators import login_required
from oauth2_provider.models import AccessToken, Application
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from integracoes.forms import IntegracaoForm
from integracoes.models import IntegracaoLegado
from portal.audit import registrar_evento_auditoria
from portal.permissions import group_required


@login_required
@group_required("Administrador")
def list(request):
    integracoes = IntegracaoLegado.objects.select_related("application").order_by("nome")
    return render(request, "integracoes/list.html", {"integracoes": integracoes})


@login_required
@group_required("Administrador")
def detail(request, pk):
    integration = get_object_or_404(IntegracaoLegado, pk=pk)
    return render(
        request,
        "integracoes/detail.html",
        {
            "integracao": integration,
            "requisicoes": integration.requisicoes.order_by("-pk")[:25],
        },
    )


@login_required
@group_required("Administrador")
def create(request):
    if request.method != "POST":
        return render(request, "integracoes/form.html", {"form": IntegracaoForm()})

    raw_secret = secrets.token_urlsafe(32)
    form = IntegracaoForm(data=request.POST)
    if not form.is_valid():
        return render(request, "integracoes/form.html", {"form": form}, status=200)

    escopos = [linha.strip() for linha in form.cleaned_data.get("escopos_texto", "").splitlines() if linha.strip()]

    with transaction.atomic():
        application = Application.objects.create(
            name=form.cleaned_data["nome"],
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_CLIENT_CREDENTIALS,
            client_secret=raw_secret,
        )
        integration = IntegracaoLegado.objects.create(
            nome=form.cleaned_data["nome"],
            application=application,
            escopos=escopos,
            criado_por=request.user,
        )
        registrar_evento_auditoria(
            acao="integracao.criada",
            objeto_tipo="integracoes.IntegracaoLegado",
            objeto_id=str(integration.public_id),
            origem="portal",
            usuario=request.user,
        )
    request.session["segredo_once"] = raw_secret
    return redirect(reverse("integracoes:rotate", args=[integration.id]))


@login_required
@group_required("Administrador")
def rotate(request, pk):
    integration = get_object_or_404(IntegracaoLegado, pk=pk)
    if request.method == "GET":
        segredo_raw = request.session.pop("segredo_once", None)
        if not segredo_raw:
            segredo_raw = secrets.token_urlsafe(32)
            integration.application.client_secret = segredo_raw
            integration.application.save()
            AccessToken.objects.filter(application=integration.application).update(expires=timezone.now())
            registrar_evento_auditoria(
                acao="integracao.credencial.rotacionada",
                objeto_tipo="integracoes.IntegracaoLegado",
                objeto_id=str(integration.public_id),
                origem="portal",
                usuario=request.user,
            )
        return render(
            request,
            "integracoes/rotate_secret.html",
            {"integracao": integration, "segredo_raw": segredo_raw},
        )
    return redirect(reverse("integracoes:detail", args=[integration.pk]))


@login_required
@group_required("Administrador")
def revoke(request, pk):
    integration = get_object_or_404(IntegracaoLegado, pk=pk)
    if request.method == "POST":
        AccessToken.objects.filter(application=integration.application).update(expires=timezone.now())
        integration.ativo = False
        integration.save(update_fields=["ativo"])
        registrar_evento_auditoria(
            acao="integracao.revogada",
            objeto_tipo="integracoes.IntegracaoLegado",
            objeto_id=str(integration.public_id),
            origem="portal",
            usuario=request.user,
        )
    return redirect(reverse("integracoes:list"))
