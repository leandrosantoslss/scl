import pytest
from django.contrib.auth import get_user_model

from integracoes.services import billing_ownership
from licencas.models import Cliente, ClienteSistema, Sistema
from licencas.tests.helpers import cliente_kwargs, data_comercial, gerar_cpf
from financeiro.services.cobrancas import gerar_cobrancas_assinatura
from datetime import date


def _assinatura(cliente_payload):
    cliente = Cliente.objects.create(**cliente_payload)
    sistema = Sistema.objects.create(nome="ERP", codigo="erp-ext")
    return ClienteSistema.objects.create(
        cliente=cliente, sistema=sistema,
        **data_comercial(),
    )


@pytest.mark.django_db
def test_gerador_ignora_assinatura_legada(policy_factory, cliente_payload):
    assinatura = _assinatura(cliente_payload)
    from oauth2_provider.models import Application

    application = Application.objects.create(
        name="Legado", client_type=Application.CLIENT_CONFIDENTIAL,
        authorization_grant_type=Application.GRANT_CLIENT_CREDENTIALS,
    )
    from integracoes.models import IntegracaoLegado

    integracao = IntegracaoLegado.objects.create(nome="Legado ERP", application=application)

    from datetime import date

    charges = gerar_cobrancas_assinatura(assinatura, ate=date(2026, 3, 5))
    assert len(charges) == 3

    usuario = get_user_model().objects.create_user("adm", password="s")
    billing_ownership.trocar_origem_cobranca(
        assinatura, integracao=integracao, usuario=usuario, motivo="cobrança migrada para legado"
    )

    charges_depois = gerar_cobrancas_assinatura(assinatura, ate=date(2027, 12, 31))
    assert charges_depois == []
    assert billing_ownership.billing_is_external(assinatura)


@pytest.mark.django_db
def test_troca_origem_exige_motivo(integration, cliente_payload):
    assinatura = _assinatura(cliente_payload)
    usuario = get_user_model().objects.create_user("adm", password="s")
    with pytest.raises(ValueError):
        billing_ownership.trocar_origem_cobranca(
            assinatura=assinatura, integracao=integration, usuario=usuario, motivo=""
        )


@pytest.mark.django_db
def test_troca_origem_audita(integration, cliente_payload):
    assinatura = _assinatura(cliente_payload)
    usuario = get_user_model().objects.create_user("adm", password="s")
    billing_ownership.trocar_origem_cobranca(
        assinatura=assinatura, integracao=integration, usuario=usuario, motivo="troca"
    )
    from portal.models import EventoAuditoria

    assert EventoAuditoria.objects.filter(acao="assinatura.origem_cobranca.trocada").exists()
