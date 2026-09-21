import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client
from django.urls import reverse

from financeiro.models import Cobranca, Pagamento
from portal.roles import CONSULTA


def _user_in_group(username, group_name):
    group, _ = Group.objects.get_or_create(name=group_name)
    user = get_user_model().objects.create_user(username, password="secret")
    user.groups.add(group)
    return user


@pytest.fixture
def financeiro_username():
    return "fin"


@pytest.fixture
def financeiro(client, financeiro_username):
    client.force_login(_user_in_group(financeiro_username, "Financeiro"))
    return client


@pytest.fixture
def consulta(client):
    client.force_login(_user_in_group("cons", CONSULTA))
    return client


@pytest.mark.django_db
def test_anonymous_redirected_to_login(client):
    assert client.get(reverse("financeiro:cobranca-list")).status_code == 302


@pytest.mark.django_db
def test_consulta_so_leitura(consulta, vencida_basica):
    _assinatura, cobranca = vencida_basica
    assert consulta.get(reverse("financeiro:cobranca-list")).status_code == 200
    assert consulta.get(reverse("financeiro:cobranca-detail", args=[cobranca.pk])).status_code == 200
    assert (
        consulta.post(
            reverse("financeiro:pagamento-registrar", args=[cobranca.pk]),
            data={"valor": "10.00", "forma": "pix"},
        ).status_code
        == 403
    )


@pytest.mark.django_db
def test_pagamento_manual_registra_e_marca_paga(financeiro, vencida_basica):
    _assinatura, cobranca = vencida_basica

    response = financeiro.post(
        reverse("financeiro:pagamento-registrar", args=[cobranca.pk]),
        data={"valor": "40.00", "forma": "pix", "pago_em": "2026-01-06T12:00"},
    
    )
    assert response.status_code == 302
    cobranca.refresh_from_db()
    assert Pagamento.objects.filter(cobranca=cobranca, valor="40.00").exists()
    assert cobranca.status == Cobranca.Status.ABERTA


@pytest.mark.django_db
def test_pagamento_com_valor_invalido_rerenderiza(financeiro, vencida_basica):
    _assinatura, cobranca = vencida_basica
    response = financeiro.post(
        reverse("financeiro:pagamento-registrar", args=[cobranca.pk]),
        data={"valor": "99999.00", "forma": "pix", "pago_em": "2026-01-06T12:00"},
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_estorno_require_post_and_updates_status(financeiro, vencida_basica):
    _assinatura, cobranca = vencida_basica
    pagamento = Pagamento.objects.create(
        cobranca=cobranca,
        valor="100.00",
        pago_em="2026-01-05T12:00:00Z",
        forma="pix",
        origem="manual",
        status="confirmed",
    )

    response = financeiro.get(
        reverse("financeiro:pagamento-estornar", args=[cobranca.pk, pagamento.pk])
    )
    assert response.status_code == 405

    response = financeiro.post(
        reverse("financeiro:pagamento-estornar", args=[cobranca.pk, pagamento.pk]),
        data={"motivo": "erro de digitação"},
    )
    assert response.status_code == 302
    pagamento.refresh_from_db()
    assert pagamento.status == Pagamento.Status.REVERSED
    cobranca.refresh_from_db()
    assert cobranca.status == Cobranca.Status.ABERTA


@pytest.mark.django_db
def test_cancelamento_portal(financeiro, vencida_basica):
    _assinatura, cobranca = vencida_basica

    response = financeiro.get(reverse("financeiro:cobranca-cancelar", args=[cobranca.pk]))
    assert response.status_code == 200

    response = financeiro.post(
        reverse("financeiro:cobranca-cancelar", args=[cobranca.pk]),
        data={"motivo": "não faz mais parte"},
    )
    assert response.status_code == 302
    cobranca.refresh_from_db()
    assert cobranca.status == Cobranca.Status.CANCELADA


@pytest.mark.django_db
def test_filters_by_status_and_date(financeiro, vencida_basica):
    _assinatura, cobranca = vencida_basica
    cliente_nome = str(cobranca.assinatura.cliente)

    content = financeiro.get(
        reverse("financeiro:cobranca-list"), data={"status": "aberta"}
    ).content.decode()
    assert cliente_nome in content

    content = financeiro.get(
        reverse("financeiro:cobranca-list"), data={"status": "paga"}
    ).content.decode()
    assert cliente_nome not in content


@pytest.mark.django_db
def test_csrf_enforced_on_payment(vencida_basica):
    _assinatura, cobranca = vencida_basica

    usuario = _user_in_group("fin", "Financeiro")
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.force_login(usuario)
    resposta = csrf_client.post(
        reverse("financeiro:pagamento-registrar", args=[cobranca.pk]),
        data={"valor": "5.00", "forma": "pix", "pago_em": "2026-01-06T12:00"},
    )
    assert resposta.status_code == 403
