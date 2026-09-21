import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from portal.audit import registrar_evento_auditoria
from portal.roles import ADMINISTRADOR, CADASTRO, CONSULTA, FINANCEIRO


def _user_in_group(username, group_name):
    group, _ = Group.objects.get_or_create(name=group_name)
    user = get_user_model().objects.create_user(username, password="secret")
    user.groups.add(group)
    return user


@pytest.mark.django_db
def test_auditoria_exige_autenticacao(client):
    response = client.get(reverse("portal:audit_list"))
    assert response.status_code == 302


@pytest.mark.django_db
def test_administrador_ve_todos_os_eventos(client):
    registrar_evento_auditoria(
        acao="financeiro.pagamento.registrado",
        objeto_tipo="financeiro.Pagamento",
        objeto_id="1",
        depois={"valor": "100.00"},
        origem="portal",
    )
    group, _ = Group.objects.get_or_create(name=ADMINISTRADOR)
    user = get_user_model().objects.create_user("adminx", password="secret")
    user.groups.add(group)
    client.force_login(user)

    response = client.get(reverse("portal:audit_list"))
    assert response.status_code == 200
    assert "financeiro.pagamento.registrado" in response.content.decode()


@pytest.mark.django_db
def test_cadastro_ve_apenas_eventos_de_cadastro(client):
    registrar_evento_auditoria(
        acao="cliente.criado",
        objeto_tipo="licencas.Cliente",
        objeto_id="1",
        depois={"nome": "Acme"},
        origem="portal",
    )
    registrar_evento_auditoria(
        acao="financeiro.pagamento.registrado",
        objeto_tipo="financeiro.Pagamento",
        objeto_id="1",
        depois={"valor": "100.00"},
        origem="portal",
    )
    group, _ = Group.objects.get_or_create(name=CADASTRO)
    user = get_user_model().objects.create_user("cad", password="secret")
    user.groups.add(group)
    client.force_login(user)

    response = client.get(reverse("portal:audit_list"))
    content = response.content.decode()
    assert "cliente.criado" in content
    assert "financeiro.pagamento.registrado" not in content


@pytest.mark.django_db
def test_financeiro_e_consulta_veem_auditoria_sanitizada(client):
    evento = registrar_evento_auditoria(
        acao="sistema.senha_rotacionada",
        objeto_tipo="licenciamento.CredencialSistema",
        objeto_id="1",
        depois={"public_id": "abc"},
        origem="system",
    )
    for role, username in ((FINANCEIRO, "fin"), (CONSULTA, "vis")):
        group, _ = Group.objects.get_or_create(name=role)
        user = get_user_model().objects.create_user(username, password="secret")
        user.groups.add(group)
        client.force_login(user)
        response = client.get(reverse("portal:audit_detail", args=[evento.public_id]))
        assert response.status_code == 200
        content = response.content.decode()
        assert "sistema.senha_rotacionada" in content
        assert "public_id" in content


@pytest.mark.django_db
def test_nenhum_valor_sensivel_aparece_na_auditoria(client):
    evento = registrar_evento_auditoria(
        acao="cliente.motivo_bloqueio",
        objeto_tipo="licencas.Cliente",
        objeto_id="1",
        depois={"document": "12345678000195"},
        origem="portal",
    )
    user = get_user_model().objects.create_superuser("root", "root@example.com", "secret")
    client.force_login(user)

    response = client.get(reverse("portal:audit_detail", args=[evento.public_id]))
    content = response.content.decode()
    assert "12345678000195" not in content
    assert "[REDACTED]" in content
