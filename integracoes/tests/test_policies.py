import pytest
from django.core.exceptions import ValidationError

from integracoes.api.exceptions import IntegrationPermissionDenied
from integracoes.models import Recurso
from integracoes.services import policies
from integracoes.services.portal_authority import rejeitar_campos_protegidos
from licencas.models import Cliente


@pytest.mark.django_db
def test_scl_master_rejects_external_write(policy_factory, integration):
    policy_factory(integration=integration, recurso=Recurso.CLIENTE, modo="scl_master")
    with pytest.raises(IntegrationPermissionDenied):
        policies.authorize_fields(
            integration, resource=Recurso.CLIENTE, operation="write", fields={"nome"}
        )


@pytest.mark.django_db
def test_shared_rejects_unlisted_field(policy_factory, integration):
    policy_factory(
        integration=integration,
        recurso=Recurso.CLIENTE,
        modo="shared",
        writable_fields=["nome"],
    )
    with pytest.raises(IntegrationPermissionDenied):
        policies.authorize_fields(
            integration, resource=Recurso.CLIENTE, operation="write", fields={"bloqueado"}
        )


@pytest.mark.django_db
def test_legacy_master_allows_listed_fields(policy_factory, integration):
    policy_factory(
        integration=integration,
        recurso=Recurso.CLIENTE,
        modo="legacy_master",
        writable_fields=["nome", "telefone"],
    )
    permitidos = policies.authorize_fields(
        integration,
        resource=Recurso.CLIENTE,
        operation="write",
        fields={"nome", "telefone"},
    )
    assert permitidos == {"nome", "telefone"}


@pytest.mark.django_db
def test_missing_policy_denies_everything(integration):
    with pytest.raises(IntegrationPermissionDenied):
        policies.authorize_fields(
            integration, resource=Recurso.CLIENTE, operation="read", fields={"nome"}
        )


def test_recurso_desconhecido(integration):
    with pytest.raises(IntegrationPermissionDenied):
        policies.authorize_fields(integration, resource="fantasma", operation="read", fields=set())


@pytest.mark.django_db
def test_portal_rejects_legacy_master_fields(policy_factory, integration, cliente_payload):
    policy_factory(
        integration=integration,
        recurso=Recurso.CLIENTE,
        modo="legacy_master",
        writable_fields=["nome"],
    )
    with pytest.raises(ValidationError) as erro:
        rejeitar_campos_protegidos(Cliente, {"nome"})
    assert "autoridade do legado" in str(erro.value)


@pytest.mark.django_db
def test_portal_permite_campos_sem_politica(cliente_payload):
    rejeitar_campos_protegidos(Cliente, {"nome"})


@pytest.mark.django_db
def test_salvar_politica_audita(policy_factory, integration):
    from django.contrib.auth import get_user_model

    usuario = get_user_model().objects.create_user("adm", password="s")
    policies.salvar_politica(
        integration=integration,
        resource=Recurso.CLIENTE,
        modo="shared",
        readable_fields=["nome"],
        writable_fields=["nome"],
        usuario=usuario,
        motivo="ativar compartilhado",
    )
    from portal.models import EventoAuditoria

    assert EventoAuditoria.objects.filter(acao="integracao.politica.alterada").exists()
