import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from licencas.models import Cliente, ClienteSistema, Sistema
from licencas.tests.helpers import cliente_kwargs, data_comercial, gerar_cpf
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


def _assinatura(nome="Acme", seed=201, **overrides):
    cliente = Cliente.objects.create(**cliente_kwargs(nome, gerar_cpf(seed)))
    sistema = Sistema.objects.create(nome="ERP", codigo=f"erp-{seed}")
    values = {"cliente": cliente, "sistema": sistema}
    values.update(data_comercial())
    values.update(overrides)
    return ClienteSistema.objects.create(**values)


@pytest.mark.django_db
def test_lista_mostra_assinaturas(cadastro):
    _assinatura()
    content = cadastro.get(reverse("licencas:assinatura-list")).content.decode()
    assert "Acme" in content


@pytest.mark.django_db
def test_cadastro_cria_assinatura(cadastro):
    cliente = Cliente.objects.create(**cliente_kwargs("Novo", gerar_cpf(301)))
    sistema = Sistema.objects.create(nome="Cad", codigo="cad-sys")
    payload = {
        "cliente": cliente.pk,
        "sistema": sistema.pk,
        "valor_recorrente": "199.90",
        "periodicidade": "monthly",
        "data_inicio": "2026-01-01",
        "primeiro_vencimento": "2026-01-05",
    }
    response = cadastro.post(reverse("licencas:assinatura-create"), data=payload)
    assert response.status_code == 302
    assert ClienteSistema.objects.filter(cliente=cliente, sistema=sistema).exists()


@pytest.mark.django_db
def test_par_duplicado_rejeitado(cadastro):
    assinatura = _assinatura()
    payload = {
        "cliente": assinatura.cliente.pk,
        "sistema": assinatura.sistema.pk,
        "valor_recorrente": "49.90",
        "periodicidade": "monthly",
        "data_inicio": "2026-02-01",
        "primeiro_vencimento": "2026-02-05",
    }
    response = cadastro.post(reverse("licencas:assinatura-create"), data=payload)
    assert response.status_code == 200
    assert "já existe" in response.content.decode().lower()


@pytest.mark.django_db
def test_estado_ativar_rejeita_get_e_aceita_post(cadastro):
    assinatura = _assinatura(ativo=False)

    response = cadastro.get(reverse("licencas:assinatura-ativar", args=[assinatura.pk]))
    assert response.status_code == 405

    assinatura.refresh_from_db()
    assert assinatura.ativo is False  # GET não executa ações

    with_primeiro = cadastro.post(
        reverse("licencas:assinatura-ativar", args=[assinatura.pk])
    )
    assert with_primeiro.status_code == 302
    assinatura.refresh_from_db()
    assert assinatura.ativo is True


@pytest.mark.django_db
def test_bloqueio_exige_motivo(cadastro):
    assinatura = _assinatura()

    without_reason = cadastro.post(
        reverse("licencas:assinatura-bloquear", args=[assinatura.pk]), data={"motivo": ""}
    )
    assert without_reason.status_code == 200
    assinatura.refresh_from_db()
    assert assinatura.bloqueado is False

    response = cadastro.post(
        reverse("licencas:assinatura-bloquear", args=[assinatura.pk]), data={"motivo": "fraude"}
    )
    assert response.status_code == 302
    assinatura.refresh_from_db()
    assert assinatura.bloqueado is True


@pytest.mark.django_db
def test_estado_desativar_post(cadastro):
    assinatura = _assinatura()
    response = cadastro.post(
        reverse("licencas:assinatura-desativar", args=[assinatura.pk]), data={"motivo": "encerrado"}
    )
    assert response.status_code == 302
    assinatura.refresh_from_db()
    assert assinatura.ativo is False


@pytest.mark.django_db
def test_consulta_so_leitura(consulta):
    assinatura = _assinatura()
    assert consulta.get(reverse("licencas:assinatura-list")).status_code == 200
    assert (
        consulta.post(reverse("licencas:assinatura-ativar", args=[assinatura.pk])).status_code
        == 403
    )
