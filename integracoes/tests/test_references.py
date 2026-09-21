import pytest
from django.contrib.auth import get_user_model
from oauth2_provider.models import Application

from integracoes.api.exceptions import IntegrationConflict, IntegrationPermissionDenied
from integracoes.models import ClienteReferenciaExterna, IntegracaoLegado, RequisicaoIntegracao
from integracoes.services import references
from licencas.models import Cliente
from licencas.tests.helpers import cliente_kwargs, gerar_cpf


def _nova_integracao(nome):
    application = Application.objects.create(
        name=nome,
        client_type=Application.CLIENT_CONFIDENTIAL,
        authorization_grant_type=Application.GRANT_CLIENT_CREDENTIALS,
    )
    return IntegracaoLegado.objects.create(nome=nome, application=application)


@pytest.mark.django_db
def test_referencia_criacao_e_busca(integration):
    cliente = Cliente.objects.create(**cliente_kwargs("Prime", gerar_cpf(301)))

    assert references.resolve_external_reference(Cliente, integration, "c-1") == (None, None)

    criada = references.obter_ou_criar_referencia(
        Cliente, integration=integration, external_id="c-1", objeto=cliente
    )
    assert criada[1] is True

    encontrada, objeto = references.resolve_external_reference(Cliente, integration, "c-1")
    assert encontrada is not None
    assert objeto.pk == cliente.pk


@pytest.mark.django_db
def test_transferir_propriedade_exige_motivo(integration):
    cliente = Cliente.objects.create(**cliente_kwargs("Acme", gerar_cpf(310)))
    referencia = ClienteReferenciaExterna.objects.create(
        integration=integration, external_id="c-9", cliente=cliente, proprietaria=True
    )
    usuario = get_user_model().objects.create_user("adm", password="s")
    nova = _nova_integracao("Outro Legado")

    with pytest.raises(IntegrationPermissionDenied):
        references.transferir_propriedade_referencia(
            referencia, nova_integracao=nova, usuario=usuario, motivo=""
        )

    result = references.transferir_propriedade_referencia(
        referencia, nova_integracao=nova, usuario=usuario, motivo="reorganização"
    )
    result.refresh_from_db()
    assert result.integration_id == nova.id


@pytest.mark.django_db
def test_transferencia_rejeita_requisicao_em_andamento(integration):
    cliente = Cliente.objects.create(**cliente_kwargs("Bora", gerar_cpf(320)))
    referencia = ClienteReferenciaExterna.objects.create(
        integration=integration, external_id="c-2", cliente=cliente, proprietaria=True
    )
    nova = _nova_integracao("Nova")

    RequisicaoIntegracao.objects.create(
        integration=nova, request_id="r1", metodo="POST", endpoint="/clientes"
    )
    usuario = get_user_model().objects.create_user("adm", password="s")

    with pytest.raises(IntegrationConflict):
        references.transferir_propriedade_referencia(
            referencia, nova_integracao=nova, usuario=usuario, motivo="m"
        )
