import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from licencas.models import Cliente
from licencas.tests.helpers import cliente_kwargs, gerar_cpf
from portal.roles import CADASTRO, CONSULTA


def _user_in_group(username, group_name):
    group, _ = Group.objects.get_or_create(name=group_name)
    user = get_user_model().objects.create_user(username, password="secret")
    user.groups.add(group)
    return user


@pytest.fixture
def cadastro(client):
    client.force_login(_user_in_group("cadastro", CADASTRO))
    return client


@pytest.fixture
def consulta(client):
    client.force_login(_user_in_group("consulta", CONSULTA))
    return client


@pytest.mark.django_db
def test_anonymous_redirected_to_login(client):
    response = client.get(reverse("licencas:cliente-list"))
    assert response.status_code == 302


@pytest.mark.django_db
def test_consulta_cannot_mutate_clients(consulta):
    response = consulta.post(reverse("licencas:cliente-create"), data={})
    assert response.status_code == 403


@pytest.mark.django_db
def test_cadastro_cria_e_atualiza_cliente(cadastro, cliente_payload):
    payload = dict(cliente_payload)
    payload["cnpjcpf"] = "12.345.678/0001-95"
    response = cadastro.post(reverse("licencas:cliente-create"), data=payload)
    assert response.status_code == 302

    created = Cliente.objects.get(cnpjcpf="12345678000195")
    assert created.nome == cliente_payload["nome"]

    payload["nome"] = "Empresa Prime"
    response = cadastro.post(
        reverse("licencas:cliente-update", args=[created.pk]), data=payload
    )
    assert response.status_code == 302
    created.refresh_from_db()
    assert created.nome == "Empresa Prime"


@pytest.mark.django_db
def test_invalid_document_rerenders_form(cadastro, cliente_payload):
    payload = dict(cliente_payload)
    payload["cnpjcpf"] = "11111111111"
    response = cadastro.post(reverse("licencas:cliente-create"), data=payload)
    assert response.status_code == 200
    assert "CNPJ" in response.content.decode() or "CPF" in response.content.decode()


@pytest.mark.django_db
def test_filters_by_name_document_and_status(consulta):
    Cliente.objects.create(**cliente_kwargs("Prime", gerar_cpf(101), bloqueado=True))
    Cliente.objects.create(**cliente_kwargs("Outro", gerar_cpf(102), ativo=False))

    content = consulta.get(reverse("licencas:cliente-list"), data={"q": "Prime"}).content.decode()
    assert "Prime" in content
    assert "Outro" not in content

    content = consulta.get(
        reverse("licencas:cliente-list"), data={"status": "blocked"}
    ).content.decode()
    assert "Prime" in content


@pytest.mark.django_db
def test_lists_are_paginated_with_25(consulta):
    for index in range(30):
        Cliente.objects.create(**cliente_kwargs(f"Cliente {index:02d}", gerar_cpf(index)))

    content = consulta.get(reverse("licencas:cliente-list")).content.decode()
    assert "Cliente 24" in content
    assert "Cliente 29" not in content


@pytest.mark.django_db
def test_detail_page_shows_cliente(consulta, cliente_payload):
    cliente = Cliente.objects.create(**cliente_payload, cnpjcpf=gerar_cpf(103))
    response = consulta.get(reverse("licencas:cliente-detail", args=[cliente.pk]))
    assert response.status_code == 200
    assert cliente_payload["nome"] in response.content.decode()
