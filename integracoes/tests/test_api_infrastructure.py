import hashlib
from datetime import datetime, timedelta, timezone as dt_timezone

import pytest
from oauth2_provider.models import AccessToken

from integracoes.models import IntegracaoLegado

from licencas.tests.helpers import gerar_cpf

TOKEN_STRING = "test-token-echo"


@pytest.fixture
def token_db(integration, db):
    token = AccessToken.objects.create(
        token=TOKEN_STRING,
        expires=datetime.now(dt_timezone.utc) + timedelta(minutes=10),
        scope="clients:read clients:write",
        application=integration.application,
        user=None,
    )
    return integration, token


def _auth(token=TOKEN_STRING):
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


@pytest.mark.django_db
def test_ping_exige_token(client, token_db):
    response = client.get("/api/v1/integrations/echo/")
    assert response.status_code == 401
    assert response.json()["code"] == "missing_or_invalid_token"


@pytest.mark.django_db
def test_token_invalido_401(client, token_db):
    response = client.get(
        "/api/v1/integrations/echo/",
        HTTP_AUTHORIZATION="Bearer token-invalido",
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_cidr_negada_403(client, integration, token_db):
    IntegracaoLegado.objects.filter(pk=integration.pk).update(
        redes_permitidas=["10.0.0.0/8"]
    )
    response = client.get("/api/v1/integrations/echo/", **_auth())
    assert response.status_code == 403
    assert response.json()["code"] == "origin_not_allowed"


@pytest.mark.django_db
def test_rate_limit_por_integracao(client, integration, token_db):
    from django.test import override_settings

    IntegracaoLegado.objects.filter(pk=integration.pk).update(limite_requisicoes=2)

    url = "/api/v1/integrations/echo/"
    assert client.get(url, **_auth()).status_code == 200
    assert client.get(url, **_auth()).status_code == 200
    resposta = client.get(url, **_auth())
    assert resposta.status_code == 429
    assert resposta.json()["code"] == "integration_rate_limited"


@pytest.mark.django_db
def test_resposta_has_envelope_ao_falhar(client, token_db):
    response = client.get("/api/v1/integrations/echo/", HTTP_AUTHORIZATION="Bearer x")
    payload = response.json()
    assert {"code", "message"}.issubset(payload.keys())
