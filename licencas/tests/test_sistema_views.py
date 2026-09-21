import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from licencas.models import Sistema
from licencas.tests.test_cliente_views import _user_in_group
from portal.roles import CADASTRO, CONSULTA


@pytest.fixture
def cadastro(client):
    client.force_login(_user_in_group("cadastro", CADASTRO))
    return client


@pytest.fixture
def consulta(client):
    client.force_login(_user_in_group("consulta", CONSULTA))
    return client


@pytest.mark.django_db
def test_consulta_cannot_mutate_systems(consulta):
    response = consulta.post(
        reverse("licencas:sistema-create"),
        data={"nome": "Novo", "codigo": "novo"},
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_cadastro_cria_sistema_e_codigo_imovel(cadastro):
    response = cadastro.post(
        reverse("licencas:sistema-create"), data={"nome": "Novo", "codigo": "novo"}
    )
    assert response.status_code == 302

    sistema = Sistema.objects.get(nome="Novo")
    response = cadastro.post(
        reverse("licencas:sistema-update", args=[sistema.pk]),
        data={"nome": "Nove", "codigo": "outro-codigo"},
    )
    assert response.status_code == 302
    sistema.refresh_from_db()
    assert sistema.nome == "Nove"
    assert sistema.codigo == "novo"  # codigo é imutável


@pytest.mark.django_db
def test_filters_systems_by_q(consulta):
    Sistema.objects.create(nome="ERP", codigo="erp")
    Sistema.objects.create(nome="CRM", codigo="crm")

    content = consulta.get(reverse("licencas:sistema-list"), data={"q": "ERP"}).content.decode()
    assert "ERP" in content
    assert "CRM" not in content
