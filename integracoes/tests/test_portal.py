import re

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from portal.roles import ADMINISTRADOR, CONSULTA


@pytest.fixture
def csrf_client():
    from django.test import Client

    return Client(enforce_csrf_checks=True)


def _user_in_group(username, group_name):
    group, _ = Group.objects.get_or_create(name=group_name)
    user = get_user_model().objects.create_user(username, password="secret")
    user.groups.add(group)
    return user


@pytest.fixture
def admin_client(client):
    client.force_login(_user_in_group("adm", ADMINISTRADOR))
    return client


@pytest.fixture
def consulta_client(client):
    client.force_login(_user_in_group("cons", CONSULTA))
    return client


@pytest.mark.django_db
def test_anonymous_redirected_to_login(client):
    assert client.get(reverse("integracoes:list")).status_code == 302


@pytest.mark.django_db
def test_consulta_nao_mutou(consulta_client):
    assert (
        consulta_client.post(reverse("integracoes:create"), data={"nome": "x"}).status_code
        == 403
    )


@pytest.mark.django_db
def test_admin_cria_integracao_e_mostra_segreto_uma_vez(admin_client):
    resposta = admin_client.post(
        reverse("integracoes:create"),
        data={"nome": "Legacy Teste", "escopos": "clients:read\npayments:write"},
    )
    assert resposta.status_code == 302
    from integracoes.models import IntegracaoLegado

    integration = IntegracaoLegado.objects.get(nome="Legacy Teste")
    assert integration.ativo is True

    from oauth2_provider.models import Application

    app = integration.application
    assert app.client_secret[:12] != ""  # hash no banco

    # Segredo aparece exatamente uma vez na resposta única (redirectTo rotate page)
    # criação direciona à página que exibe o segredo UMA única vez.
    resposta_redirect = admin_client.get(
        reverse("integracoes:rotate", args=[integration.pk])
    )
    page = resposta_redirect.content.decode()
    match = re.search(r'<code>([^<]+)</code>', page)
    assert match is not None

    # Chamar rotate de novo gera um NOVO segredo (nunca o mesmo).
    outra = admin_client.get(reverse("integracoes:rotate", args=[integration.pk]))
    outra_content = outra.content.decode()
    ligado = re.search(r'<code>([^<]+)</code>', outra_content)
    assert ligado.group(1) != match.group(1)


@pytest.mark.django_db
def test_csrf_enforced_ao_criar(csrf_client):
    admin = _user_in_group("adm-csrf", ADMINISTRADOR)
    csrf_client.force_login(admin)
    resposta = csrf_client.post(
        reverse("integracoes:create"), data={"nome": "CSRF", "escopos": ""}
    )
    assert resposta.status_code == 403
