from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from licencas.forms.assinaturas import AssinaturaForm
from licencas.models import ClienteSistema
from licencas.selectors import listar_assinaturas
from licencas.services import assinaturas as domain_services
from portal.permissions import group_required


@login_required
def assinatura_list(request):
    assinaturas = listar_assinaturas(
        cliente=request.GET.get("cliente", ""),
        sistema=request.GET.get("sistema", ""),
        periodicidade=request.GET.get("periodicidade", ""),
        status=request.GET.get("status", ""),
    )
    paginator = Paginator(assinaturas, 25)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "licencas/assinaturas/list.html", {"page": page})


@login_required
def assinatura_detail(request, pk):
    assinatura = get_object_or_404(
        ClienteSistema.objects.select_related("cliente", "sistema"), pk=pk
    )
    return render(request, "licencas/assinaturas/detail.html", {"assinatura": assinatura})


def _form(request, instance=None):
    if request.method == "POST":
        return AssinaturaForm(request.POST, instance=instance)
    return AssinaturaForm(instance=instance)


@login_required
@group_required("Cadastro")
def assinatura_create(request):
    if request.method == "POST":
        form = _form(request)
        if form.is_valid():
            domain_services.criar_assinatura(form=form, usuario=request.user)
            return redirect(reverse("licencas:assinatura-list"))
        else:
            not_save = True
            return render(
                request,
                "licencas/assinaturas/form.html",
                {"form": form},
            )
    else:
        form = _form(request)
    return render(request, "licencas/assinaturas/form.html", {"form": form})


@login_required
@group_required("Cadastro")
def assinatura_update(request, pk):
    assinatura = get_object_or_404(ClienteSistema, pk=pk)
    if request.method == "POST":
        form = _form(request, instance=assinatura)
        if form.is_valid():
            domain_services.atualizar_comercial_form(
                assinatura=assinatura, form=form, usuario=request.user
            )
            return redirect(reverse("licencas:assinatura-detail", args=[assinatura.pk]))
    else:
        form = _form(request, instance=assinatura)
    return render(request, "licencas/assinaturas/form.html", {"form": form, "assinatura": assinatura})


def _cadastro_action(view):
    @login_required
    @group_required("Cadastro")
    def wrapped(request, *args, **kwargs):
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        return view(request, *args, **kwargs)
    return wrapped


@login_required
@group_required("Cadastro")
def assinatura_ativar(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    assinatura = get_object_or_404(ClienteSistema, pk=pk)
    domain_services.ativar_assinatura(assinatura, usuario=request.user)
    return redirect(reverse("licencas:assinatura-detail", args=[assinatura.pk]))


@login_required
@group_required("Cadastro")
def assinatura_bloquear(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    assinatura = get_object_or_404(ClienteSistema, pk=pk)
    motivo = request.POST.get("motivo", "")
    if not motivo.strip():
        return render(
            request,
            "licencas/assinaturas/confirm_action.html",
            {"assinatura": assinatura, "motivo_erro": "Informe o motivo do bloqueio."},
            status=200,
        )
    domain_services.bloquear_assinatura(
        assinatura=assinatura, motivo=motivo, usuario=request.user
    )
    return redirect(reverse("licencas:assinatura-detail", args=[assinatura.pk]))


@login_required
@group_required("Cadastro")
def assinatura_desbloquear(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    assinatura = get_object_or_404(ClienteSistema, pk=pk)
    domain_services.desbloquear_assinatura(assinatura, usuario=request.user)
    return redirect(reverse("licencas:assinatura-detail", args=[assinatura.pk]))


@login_required
@group_required("Cadastro")
def assinatura_desativar(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    assinatura = get_object_or_404(ClienteSistema, pk=pk)
    domain_services.desativar_assinatura(
        assinatura, motivo=request.POST.get("motivo", "encerrado"), usuario=request.user
    )
    return redirect(reverse("licencas:assinatura-detail", args=[assinatura.pk]))
