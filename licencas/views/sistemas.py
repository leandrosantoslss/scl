from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from licencas.forms.sistemas import SistemaForm
from licencas.models import Sistema
from licencas.selectors import listar_sistemas
from licencas.services import clientes as domain_services
from portal.permissions import group_required


@login_required
def sistema_list(request):
    sistemas = listar_sistemas(
        q=request.GET.get("q", ""), status=request.GET.get("status", "")
    )
    paginator = Paginator(sistemas, 25)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "licencas/sistemas/list.html", {"page": page})


@login_required
def sistema_detail(request, pk):
    sistema = get_object_or_404(Sistema, pk=pk)
    return render(request, "licencas/sistemas/detail.html", {"sistema": sistema})


@login_required
@group_required("Cadastro")
def sistema_create(request):
    if request.method == "POST":
        form = SistemaForm(request.POST)
        if form.is_valid():
            domain_services.criar_sistema(form=form, usuario=request.user)
            return redirect(reverse("licencas:sistema-list"))
    else:
        form = SistemaForm()
    return render(request, "licencas/sistemas/form.html", {"form": form})


@login_required
@group_required("Cadastro")
def sistema_update(request, pk):
    sistema = get_object_or_404(Sistema, pk=pk)
    if request.method == "POST":
        form = SistemaForm(request.POST, instance=sistema)
        if form.is_valid():
            domain_services.atualizar_sistema(
                sistema=sistema, form=form, usuario=request.user
            )
            return redirect(reverse("licencas:sistema-detail", args=[sistema.pk]))
    else:
        form = SistemaForm(instance=sistema)
    return render(request, "licencas/sistemas/form.html", {"form": form, "sistema": sistema})
