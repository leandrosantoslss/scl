import base64
import secrets

import pytest
from oauth2_provider.models import Application

from integracoes.models import IntegracaoLegado


@pytest.fixture
def basic_auth():
    def build(client_id, secret):
        encoded = base64.b64encode(f"{client_id}:{secret}".encode()).decode()
        return f"Basic {encoded}"

    return build


@pytest.fixture
def integration_factory(db):
    from itertools import count

    seq = count(1)

    def factory(scopes=None):
        numero = next(seq)
        raw_secret = secrets.token_urlsafe(32)
        application = Application.objects.create(
            name=f"Legacy ERP {numero}",
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_CLIENT_CREDENTIALS,
            client_secret=raw_secret,
        )
        integration = IntegracaoLegado.objects.create(
            nome=f"Legacy ERP {numero}",
            application=application,
            escopos=scopes or [],
        )
        return integration, raw_secret

    return factory


@pytest.fixture
def integration(integration_factory):
    return integration_factory(scopes=["clients:read", "clients:write"])[0]


@pytest.fixture
def policy_factory(db):
    from integracoes.models import PoliticaIntegracao

    def factory(**values):
        defaults = {"readable_fields": [], "writable_fields": []}
        defaults.update(values)
        return PoliticaIntegracao.objects.create(**defaults)

    return factory
