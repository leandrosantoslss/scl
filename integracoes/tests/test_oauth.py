import pytest
from django.utils import timezone
from datetime import timedelta

from integracoes.models import IntegracaoLegado


TOKEN_URL = "/api/v1/integrations/token/"


@pytest.mark.django_db
def test_client_credentials_returns_short_lived_token(client, integration_factory, basic_auth):
    integration, raw_secret = integration_factory(scopes=["clients:read"])
    response = client.post(
        TOKEN_URL,
        {"grant_type": "client_credentials", "scope": "clients:read"},
        HTTP_AUTHORIZATION=basic_auth(integration.application.client_id, raw_secret),
    )
    assert response.status_code == 200
    assert response.json()["expires_in"] <= 900


@pytest.mark.django_db
def test_inactive_integration_is_rejected(client, integration_factory, basic_auth):
    integration, raw_secret = integration_factory(scopes=["clients:read"])
    integration.ativo = False
    integration.save()
    response = client.post(
        TOKEN_URL,
        {"grant_type": "client_credentials", "scope": "clients:read"},
        HTTP_AUTHORIZATION=basic_auth(integration.application.client_id, raw_secret),
    )
    assert response.status_code in {401, 403}


@pytest.mark.django_db
def test_expired_credential_is_rejected(client, integration_factory, basic_auth):
    integration, raw_secret = integration_factory(scopes=["clients:read"])
    integration.credencial_expira_em = timezone.now() - timedelta(hours=1)
    integration.save()
    response = client.post(
        TOKEN_URL,
        {"grant_type": "client_credentials", "scope": "clients:read"},
        HTTP_AUTHORIZATION=basic_auth(integration.application.client_id, raw_secret),
    )
    assert response.status_code in {401, 403}


@pytest.mark.django_db
def test_invalid_secret_is_rejected(client, integration_factory, basic_auth):
    integration, raw_secret = integration_factory(scopes=["clients:read"])
    response = client.post(
        TOKEN_URL,
        {"grant_type": "client_credentials", "scope": "clients:read"},
        HTTP_AUTHORIZATION=basic_auth(integration.application.client_id, "senha-errada"),
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_scope_escalation_is_rejected(client, integration_factory, basic_auth):
    integration, raw_secret = integration_factory(scopes=["clients:read"])
    response = client.post(
        TOKEN_URL,
        {"grant_type": "client_credentials", "scope": "payments:write clients:read"},
        HTTP_AUTHORIZATION=basic_auth(integration.application.client_id, raw_secret),
    )
    assert response.status_code in {400, 403}


@pytest.mark.django_db
def test_denied_cidr_is_rejected(client, integration_factory, basic_auth):
    integration, raw_secret = integration_factory(scopes=["clients:read"])
    integration.redes_permitidas = ["10.0.0.0/8"]
    integration.save()
    response = client.post(
        TOKEN_URL,
        {"grant_type": "client_credentials", "scope": "clients:read"},
        HTTP_AUTHORIZATION=basic_auth(integration.application.client_id, raw_secret),
        REMOTE_ADDR="203.0.113.5",
    )
    assert response.status_code in {401, 403}


@pytest.mark.django_db
def test_ultimo_uso_atualiza_somente_no_sucesso(client, integration_factory, basic_auth):
    integration, raw_secret = integration_factory(scopes=["clients:read"])

    integration.refresh_from_db()
    antes = integration.ultimo_uso_em

    response = client.post(
        TOKEN_URL,
        {"grant_type": "client_credentials", "scope": "clients:read"},
        HTTP_AUTHORIZATION=basic_auth(integration.application.client_id, raw_secret),
    )
    assert response.status_code == 200
    integration.refresh_from_db()
    assert integration.ultimo_uso_em is not None
    if integration.ultimo_uso_em is not None:
        assert antes is None or integration.ultimo_uso_em >= antes

    # Falha não atualiza.
    integration.ultimo_uso_em = None
    integration.save()
    IntegracaoLegado.objects.filter(pk=integration.pk).update(ultimo_uso_em=None)
    falha = client.post(
        TOKEN_URL,
        {"grant_type": "client_credentials", "scope": "clients:read"},
        HTTP_AUTHORIZATION=basic_auth(integration.application.client_id, "errada"),
    )
    assert falha.status_code == 401
    integration.refresh_from_db()
    assert integration.ultimo_uso_em is None
