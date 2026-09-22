from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from financeiro.forms import ConfiguracaoForm, MotivoForm, PagamentoManualForm
from financeiro.models import Cobranca, ConfiguracaoFinanceira, Pagamento
from financeiro.selectors import saldo_cobranca
from financeiro.services import pagamentos as pagamento_services
from financeiro.services import configuracao as config_services
from portal.permissions import group_required


def _listar_cobrancas(request):
    queryset = Cobranca.objects.select_related(
        "assinatura", "assinatura__cliente", "assinatura__sistema"
    ).order_by("vencimento", "pk")

    status = request.GET.get("status", "")
    if status in Cobranca.Status.values:
        queryset = queryset.filter(status=status)
    vencimento_de = request.GET.get("vencimento_de", "")
    if vencimento_de:
        queryset = queryset.filter(vencimento__gte=vencimento_de)
    vencimento_ate = request.GET.get("vencimento_ate", "")
    if vencimento_ate:
        queryset = queryset.filter(vencimento__lte=vencimento_ate)
    cliente = request.GET.get("cliente", "")
    if cliente:
        queryset = queryset.filter(assinatura__cliente_id=cliente)
    sistema = request.GET.get("sistema", "")
    if sistema:
        queryset = queryset.filter(assinatura__sistema_id=sistema)
    return queryset


@login_required
def cobranca_list(request):
    cobrancas = _listar_cobrancas(request)
    paginator = Paginator(cobrancas, 25)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "financeiro/cobrancas/list.html", {"page": page})


@login_required
def cobranca_detail(request, pk):
    cobranca = get_object_or_404(
        Cobranca.objects.select_related(
            "assinatura", "assinatura__cliente", "assinatura__sistema"
        ),
        pk=pk,
    )
    pagamentos = cobranca.pagamentos.all().order_by("pk")
    return render(
        request,
        "financeiro/cobrancas/detail.html",
        {
            "cobranca": cobranca,
            "saldo": saldo_cobranca(cobranca),
            "pagamentos": pagamentos,
        },
    )


def _financeiro_required(request):
    if not request.user.is_superuser and not request.user.groups.filter(
        name__in=["Financeiro", "Administrador"]
    ).exists():
        raise PermissionDenied


@login_required
@group_required("Financeiro", "Administrador")
def pagamento_registrar(request, pk):
    cobranca = get_object_or_404(Cobranca, pk=pk)
    form = PagamentoManualForm(data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            pagamento_services.registrar_pagamento_manual(
                cobranca=cobranca,
                valor=form.cleaned_data["valor"],
                pago_em=form.cleaned_data["pago_em"],
                forma=form.cleaned_data["forma"],
                usuario=request.user,
            )
            return redirect(reverse("financeiro:cobranca-detail", args=[cobranca.pk]))
        except ValidationError:
            form.add_error(None, "Pagamento não concluído: valor pode ter superado o saldo.")
    form = PagamentoManualForm(initial={"pago_em": timezone.localtime()})
    return render(
        request,
        "financeiro/pagamentos/form.html",
        {"cobranca": cobranca, "form": form},
    )


@login_required
@group_required("Financeiro", "Administrador")
def pagamento_estornar(request, cobranca_pk, pk):
    pagamento = get_object_or_404(Pagamento, pk=pk, cobranca_id=cobranca_pk)
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    form = MotivoForm(data=request.POST or None)
    if form.is_valid():
        try:
            pagamento_services.estornar_pagamento(
                pagamento=pagamento,
                motivo=form.cleaned_data["motivo"],
                usuario=request.user,
            )
        except ValidationError:
            form.add_error(None, "Estorno não concluído: verifique o estado do pagamento.")
        else:
            return redirect(reverse("financeiro:cobranca-detail", args=[cobranca_pk]))
    return render(
        request,
        "financeiro/pagamentos/reverse.html",
        {"cobranca_pk": cobranca_pk, "pagamento": pagamento, "form": form},
        status=200,
    )


@login_required
def cobranca_cancelar(request, pk):
    cobranca = get_object_or_404(Cobranca, pk=pk)
    if request.method == "POST":
        _financeiro_required(request)
        form = MotivoForm(data=request.POST)
        if form.is_valid():
            pagamento_services.cancelar_cobranca_scl(
                cobranca=cobranca,
                motivo=form.cleaned_data["motivo"],
                usuario=request.user,
            )
            return redirect(reverse("financeiro:cobranca-detail", args=[cobranca.pk]))
        return render(
            request,
            "financeiro/cobrancas/cancel.html",
            {"cobranca": cobranca, "form": form},
            status=200,
        )
    _financeiro_required(request)
    return render(
        request,
        "financeiro/cobrancas/cancel.html",
        {"cobranca": cobranca, "form": MotivoForm()},
    )


@login_required
@group_required("Administrador")
def configuracao_editar(request):
    config, _ = ConfiguracaoFinanceira.objects.get_or_create(pk=1)
    if request.method == "POST":
        form = ConfiguracaoForm(data=request.POST, instance=config)
        if form.is_valid():
            config_services.alterar_configuracao_financeira(
                values=form.cleaned_data, usuario=request.user, motivo="via portal"
            )
            return redirect(reverse("financeiro:configuracao-editar"))
    else:
        form = ConfiguracaoForm(instance=config)
    return render(
        request,
        "financeiro/configuracao/form.html",
        {"config": config, "form": form},
    )


@login_required
def pagamento_list(request):
    pagamentos = Pagamento.objects.select_related("cobranca").order_by("-pk")
    paginator = Paginator(pagamentos, 25)
    page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "financeiro/pagamentos/list.html",
        {"page": page},
    )


from financeiro.services import emissoes as emissoes_services
from financeiro.models import ContaGateway, EmissaoCobranca
import secrets
from django.http import HttpResponseNotAllowed


def _financeiro_required(request):
    from django.contrib import __package__ as _p  # noqa: F401

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if not request.user.is_superuser and not request.user.groups.filter(name__in=["Financeiro", "Administrador"]).exists():
        from django.core.exceptions import PermissionDenied

        raise PermissionDenied


def _contas_para_meio(meio):
    from django.db.models import Q

    return ContaGateway.objects.filter(
        Q(ativo=True) & (Q(habilita_pix=True) | Q(habilita_boleto=True))
    )


def _criada_post(request, cobranca_pk):
    cobranca = get_object_or_404(Cobranca, pk=cobranca_pk)
    _financeiro_required(request)
    conta_pk = request.POST.get("conta", "")
    meio = request.POST.get("meio", "pix")
    if not conta_pk or meio not in ("pix", "boleto"):
        return redirect(reverse("financeiro:cobranca-detail", args=[cobranca.pk]))
    try:
        conta = ContaGateway.objects.get(pk=conta_pk, ativo=True)
    except ContaGateway.DoesNotExist:
        conta = None
    emissoes_services.emitir_cobranca(
        cobranca=cobranca,
        conta=conta,
        meio=meio,
        idempotencia=secrets.token_hex(8),
        usuario=request.user,
    )
    from django.db.models import Q
    return redirect(reverse("financeiro:cobranca-detail", args=[cobranca.pk]))


def emissao_criar(request, cobranca_pk):
    return _criada_post(request, cobranca_pk)


def emissao_detalhar(request, pk):
    emissao = get_object_or_404(EmissaoCobranca, pk=pk)
    return render(request, "financeiro/emissoes/detail.html", {"emissao": emissao})


def emissao_cancelar(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    _financeiro_required(request)
    emissao = get_object_or_404(EmissaoCobranca, pk=pk)
    motivo = request.POST.get("motivo", "")
    try:
        emissoes_services.cancelar_emissao(emissao, idempotencia=secrets.token_hex(8), usuario=request.user)
    except Exception:
        emissao.erro_normalizado = "Cancelamento com resultado indefinido."
        emissao.save()
    return redirect(reverse("financeiro:cobranca-detail", args=[emissao.cobranca_id]))


from financeiro.forms import ContaGatewayForm
from financeiro.services import contas_gateway
import os, json as _json  # noqa: F401


def _admin_required(request):
    from django.core.exceptions import PermissionDenied

    if not request.user.is_superuser and not request.user.groups.filter(name__in=["Administrador"]).exists():
        raise PermissionDenied


@login_required
def gateway_list(request):
    _admin_required(request)
    contas = ContaGateway.objects.all().order_by("provedor", "nome")
    return render(request, "financeiro/gateways/list.html", {"contas": contas})


@login_required
def gateway_create(request):
    _admin_required(request)
    if request.method == "POST":
        form = ContaGatewayForm(data=request.POST)
        if form.is_valid():
            from financeiro.crypto import encrypt_config
            if form.cleaned_data.get("configuracao_texto"):
                try:
                    import json as _js
                    parsed = _js.loads(form.cleaned_data.get("configuracao_texto") or "{}")
                except Exception:
                    pass
            form.save(commit=False)
            config_parsed = form.cleaned_data.pop("configuracao_texto", {})
            form.cleaned_data["configuracao_criptografada"] = ""
            with transaction.atomic():
                conta = form.save(commit=False)
                conta.configuracao_criptografada = ""
                # será substituído no salvar_credenciais
                conta.full_clean()
                conta.save()
                from financeiro.services.contas_gateway import salvar_credenciais
                if config_parsed:
                    salvar_credenciais(conta=conta, configuracao=config_parsed, usuario=request.user)
            return redirect(reverse("financeiro:gateway-list"))
    else:
        form = ContaGatewayForm()
    return render(request, "financeiro/gateways/form.html", {"form": form})


@login_required
def gateway_detail(request, pk):
    _admin_required(request)
    conta = get_object_or_404(ContaGateway, pk=pk)
    return render(request, "financeiro/gateways/detail.html", {"conta": conta})


@login_required
def gateway_editar(request, pk):
    _admin_required(request)
    conta = get_object_or_404(ContaGateway, pk=pk)
    if request.method == "POST":
        from financeiro.services.contas_gateway import salvar_credenciais

        form = ContaGatewayForm(data=request.POST, instance=conta)
        if form.is_valid():
            form.save(commit=False)
            form.instance.alterado_por = request.user
            config_parsed = form.cleaned_data.pop("configuracao_texto", {})
            from django.db import transaction

            with transaction.atomic():
                instance = form.save()
                if config_parsed:
                    salvar_credenciais(conta=instance, configuracao=config_parsed, usuario=request.user)
            return redirect(reverse("financeiro:gateway-list"))
    else:
        form = ContaGatewayForm(instance=conta)
    return render(request, "financeiro/gateways/form.html", {"form": form, "conta": conta})


@login_required
def gateway_ativar_desativar(request, pk):
    _admin_required(request)
    conta = get_object_or_404(ContaGateway, pk=pk)
    if request.method == "POST":
        from financeiro.services.contas_gateway import ativar_conta, desativar_conta

        if conta.ativo:
            desativar_conta(conta=conta, usuario=request.user, motivo="via portal")
        else:
            ativar_conta(conta=conta, usuario=request.user)
    return redirect(reverse("financeiro:gateway-list"))
