import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from financeiro.gateways.fake import FakeAdapter
from financeiro.gateways.registry import register_adapter
from financeiro.models import Cobranca, ContaGateway, EmissaoCobranca
from financeiro.services import emissoes
from licencas.models import Cliente, ClienteSistema, Sistema
from licencas.tests.helpers import gerar_cpf
from portal.roles import FINANCEIRO


@pytest.fixture(autouse=True)
def _registrar_fake():
    from financeiro.gateways import registry
    from financeiro.gateways.fake import FakeAdapter as FA

    FakeAdapter._SHARED_EMITIDOS.clear()
    FakeAdapter._SHARED_PEDIDOS.clear()
    registry.FACTORIES["fake"] = lambda **kwargs: FakeAdapter(**kwargs)
    yield


@pytest.fixture
def financeiro_client(client):
    group, _ = Group.objects.get_or_create(name=FINANCEIRO)
    user = get_user_model().objects.create_user("fin", password="secret")
    user.groups.add(group)
    client.force_login(user)
    return client


@pytest.fixture
def cobranca_com_conta(db, cliente_payload):
    cliente = Cliente.objects.create(**cliente_payload)
    sistema = Sistema.objects.create(nome="Ey", codigo="erp-view")
    assinatura = ClienteSistema.objects.create(
        cliente=cliente, sistema=sistema,
        valor_recorrente="20.00", periodicidade="monthly",
        data_inicio="2026-01-01", primeiro_vencimento="2026-01-05",
    )
    cobranca = Cobranca.objects.create(
        assinatura=assinatura,
        competencia="2026-01-01",
        vencimento="2026-01-05",
        fim_carencia="2026-01-10",
        valor_original="20.00",
    )
    conta = ContaGateway.objects.create(nome="Conta PVirtual", provedor="fake", habilita_pix=True)
    return cobranca, conta


@pytest.mark.django_db
def test_fluxo_portal_emissao(financeiro_client, cobranca_com_conta):
    cobranca, conta = cobranca_com_conta

    form_url = reverse("financeiro:emissao-criar", args=[cobranca.pk])
    resposta = financeiro_client.post(
        form_url,
        data={
            "conta": conta.pk,
            "meio": "pix",
        },
    )
    assert resposta.status_code == 302

    emissao = EmissaoCobranca.objects.first()
    assert emissao is not None

    detach_url = reverse("financeiro:emissao-cancelar", args=[emissao.pk])
    resposta = financeiro_client.post(
        detach_url, data={"motivo": "cancelar"}
    )
    assert resposta.status_code == 302
    emissao.refresh_from_db()
    assert emissao.status == EmissaoCobranca.Status.CANCELLED


@pytest.mark.django_db
def test_anonymous_redirect_does_not_mutate(client, cobranca_com_conta):
    cobranca, _conta = cobranca_com_conta
    resposta = client.post(reverse("financeiro:emissao-criar", args=[cobranca.pk]), data={"conta": 1, "meio": "pix"})
    assert resposta.status_code in {302, 403}
