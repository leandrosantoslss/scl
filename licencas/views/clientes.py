from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from licencas.forms.clientes import ClienteForm
from licencas.models import Cliente
from licencas.selectors import listar_clientes
from licencas.services import clientes as cliente_services
from portal.permissions import group_required


PERMITIDOS_CADASTRO = ["Cadastro"]


@login_required
def cliente_list(request):
    clientes = listar_clientes(
        q=request.GET.get("q", ""), status=request.GET.get("status", "")
    )
    paginator = Paginator(clientes, 25)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "licencas/clientes/list.html", {"page": page})


@login_required
def cliente_detail(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    return render(request, "licencas/clientes/detail.html", {"cliente": cliente})


def _cliente_view(form_context, request, cliente=None):
    pass


@login_required
@group_required("Cadastro")
def cliente_create(request):
    if request.method == "POST":
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente_services.criar_cliente(form=form, usuario=request.user)
            return redirect(reverse("licencas:cliente-list"))
    else:
        form = ClienteForm()
    return render(request, "licencas/clientes/form.html", {"form": form})


@login_required
@group_required("Cadastro")
def cliente_update(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == "POST":
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            try:
                cliente_services.atualizar_cliente(
                    cliente=cliente, form=form, usuario=request.user
                )
            except ValidationError:
                return render(
                    request,
                    "licencas/clientes/form.html",
                    {"form": form, "cliente": cliente},
                    status=200,
                )
            return redirect(reverse("licencas:cliente-detail", args=[cliente.pk]))
    else:
        form = ClienteForm(instance=cliente)
    return render(request, "licencas/clientes/form.html", {"form": form, "cliente": cliente})


@login_required
@group_required("Cadastro")
def cliente_bloquear(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == "POST":
        cliente_services.bloquear_cliente(
            cliente=cliente, motivo=request.POST.get("motivo_bloqueio", ""), usuario=request.user
        )
    return redirect(reverse("licencas:cliente-detail", args=[cliente.pk]))


@login_required
@group_required("Cadastro")
def cliente_desbloquear(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == "POST":
        cliente_services.desbloquear_cliente(cliente=cliente, usuario=request.user)
    return redirect(reverse("licencas:cliente-detail", args=[cliente.pk]))
