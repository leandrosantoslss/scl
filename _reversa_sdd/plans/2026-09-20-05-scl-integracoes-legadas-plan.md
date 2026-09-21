# SCL Legacy Integrations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir que sistemas legados consultem e alimentem clientes, assinaturas, cobranças e pagamentos com autoridade configurável, idempotência e conflitos explícitos.

**Architecture:** Criar o app `integracoes` e uma API DRF separada da API de licenciamento. OAuth2 Client Credentials autentica cada legado; policies e referências externas controlam autoridade e identidade sem acoplar o domínio aos consumidores.

**Tech Stack:** Django REST Framework, django-oauth-toolkit, PostgreSQL, pytest-django.

**Spec:** `_reversa_sdd/specs/2026-09-20-scl-licenciamento-financeiro-design.md`

## Global Constraints

- O legado sempre inicia a comunicação; sem polling e sem webhook de saída.
- Lotes têm no máximo 100 itens e transação independente por item.
- `external_id` é obrigatório e único por integração/recurso.
- Sem política de última gravação; modo compartilhado exige versão/ETag.
- Só uma integração pode ser proprietária de um registro.
- Cada assinatura tem uma única origem geradora de cobranças.
- Uma integração estorna apenas pagamentos criados por ela.
- A API passa pelos mesmos serviços de domínio do portal.
- Commits somente com autorização.

---

### Task 1: OAuth2 Integration Identity

**Files:**
- Modify: `requirements.txt`
- Create: `integracoes/__init__.py`
- Create: `integracoes/apps.py`
- Create: `integracoes/models.py`
- Create: `integracoes/migrations/__init__.py`
- Create: `integracoes/tests/__init__.py`
- Create: `integracoes/tests/conftest.py`
- Create: `integracoes/tests/test_oauth.py`
- Modify: `app/settings.py`
- Modify: `app/urls.py`

**Interfaces:**
- Produces: `IntegracaoLegado` linked one-to-one to OAuth Toolkit `Application`.
- Produces: `POST /api/v1/integrations/token/` using Client Credentials.
- Produces: scopes `clients:*`, `subscriptions:*`, `finance:*`, `payments:*`.

- [ ] **Step 1: Add API dependencies**

Add:

```text
djangorestframework>=3.16,<3.17
django-oauth-toolkit>=3.0,<4
```

- [ ] **Step 2: Write failing token tests**

Create the integration fixtures:

```python
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
    def factory(scopes=None):
        raw_secret = secrets.token_urlsafe(32)
        application = Application.objects.create(
            name="Legacy ERP",
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_CLIENT_CREDENTIALS,
            client_secret=raw_secret,
        )
        integration = IntegracaoLegado.objects.create(
            nome="Legacy ERP",
            application=application,
            escopos=scopes or [],
        )
        return integration, raw_secret
    return factory


@pytest.fixture
def integration(integration_factory):
    return integration_factory(scopes=["clients:read", "clients:write"])[0]
```

Then add the OAuth tests:

```python
import pytest
from oauth2_provider.models import Application


@pytest.mark.django_db
def test_client_credentials_returns_short_lived_token(client, integration_factory, basic_auth):
    integration, raw_secret = integration_factory(scopes=["clients:read"])
    response = client.post(
        "/api/v1/integrations/token/",
        {"grant_type": "client_credentials", "scope": "clients:read"},
        HTTP_AUTHORIZATION=basic_auth(integration.application.client_id, raw_secret),
    )
    assert response.status_code == 200
    assert response.json()["expires_in"] <= 900
```

Also test inactive/expired integration, invalid secret, scope escalation, denied source CIDR and `ultimo_uso_em` changing only after successful authentication.

- [ ] **Step 3: Verify tests fail**

Run: `SECRET_KEY=test-only-key python -m pytest integracoes/tests/test_oauth.py -v`

Expected: app/dependency missing.

- [ ] **Step 4: Configure OAuth Toolkit and DRF**

```python
INSTALLED_APPS += ["rest_framework", "oauth2_provider", "integracoes"]
OAUTH2_PROVIDER = {
    "ACCESS_TOKEN_EXPIRE_SECONDS": 900,
    "SCOPES": {
        "clients:read": "Consultar clientes",
        "clients:write": "Alterar clientes",
        "subscriptions:read": "Consultar assinaturas",
        "subscriptions:write": "Alterar assinaturas",
        "finance:read": "Consultar financeiro",
        "finance:write": "Alterar cobranças",
        "payments:write": "Registrar pagamentos",
        "payments:reverse": "Estornar pagamentos próprios",
    },
}
```

Use `OAuth2Authentication` only on integration API views; do not make it the global portal authentication backend. Wrap the token view/validator so inactive or expired integrations and requests outside configured CIDRs are rejected before token issuance. Successful token/API authentication updates `ultimo_uso_em` with a throttled database write; failures do not.

- [ ] **Step 5: Implement IntegracaoLegado**

Use exact field names: `public_id` UUID, `nome`, `application` one-to-one, `ativo`, `escopos` JSON, `limite_requisicoes`, `redes_permitidas` JSON, `credencial_expira_em`, `ultimo_uso_em`, `criado_por`, `alterado_por`, `criado_em`, `alterado_em`.

- [ ] **Step 6: Run migrations and OAuth tests**

Run: `SECRET_KEY=test-only-key DATABASE_URL="$SCL_TEST_DATABASE_URL" python manage.py makemigrations integracoes`

Run: `SECRET_KEY=test-only-key DATABASE_URL="$SCL_TEST_DATABASE_URL" python manage.py migrate`

Run: `SECRET_KEY=test-only-key python -m pytest integracoes/tests/test_oauth.py -v`

Expected: PASS.

- [ ] **Step 7: Suggested commit**

```bash
git add requirements.txt app/settings.py app/urls.py integracoes
git commit -m "feat: authenticate legacy integrations with oauth2"
```

### Task 2: Policies, External References, and Billing Ownership

**Files:**
- Modify: `integracoes/models.py`
- Create: `integracoes/services/__init__.py`
- Create: `integracoes/services/policies.py`
- Create: `integracoes/services/references.py`
- Create: `integracoes/services/billing_ownership.py`
- Create: `integracoes/tests/test_policies.py`
- Create: `integracoes/tests/test_references.py`
- Create: `integracoes/tests/test_portal_authority.py`
- Create: `integracoes/tests/test_billing_ownership.py`
- Modify: `integracoes/tests/conftest.py`
- Modify: `licencas/services/clientes.py`
- Modify: `licencas/services/sistemas.py`
- Modify: `licencas/services/assinaturas.py`
- Modify: `licencas/views/clientes.py`
- Modify: `licencas/views/assinaturas.py`
- Modify: `financeiro/views.py`
- Modify: `licencas/forms/clientes.py`
- Modify: `licencas/forms/assinaturas.py`
- Modify: `financeiro/forms.py`
- Modify: `financeiro/services/cobrancas.py`
- Modify: `financeiro/services/pagamentos.py`
- Modify: `licencas/tests/test_cliente_views.py`
- Modify: `licencas/tests/test_assinatura_views.py`
- Modify: `financeiro/tests/test_views.py`
- Create: migrations in `integracoes/migrations/`

**Interfaces:**
- Produces: `PoliticaIntegracao`, four concrete reference models, `AssinaturaOrigemCobranca`, `RequisicaoIntegracao`.
- Produces: `IntegrationPermissionDenied` and `IntegrationConflict` domain exceptions.
- Produces: `authorize_fields(integration, *, resource, operation, fields)`.
- Produces: `resolve_external_reference(model, integration, external_id)`.
- Produces: `billing_is_external(assinatura) -> bool`.
- Produces: `trocar_origem_cobranca(assinatura, *, integracao, usuario, motivo)`.
- Produces: `transferir_propriedade_referencia(referencia, *, nova_integracao, usuario, motivo)`.

- [ ] **Step 1: Write failing policy matrix tests**

Move the policy-only fixture into `integracoes/tests/conftest.py` in this task, after `PoliticaIntegracao` exists:

```python
from integracoes.models import PoliticaIntegracao


@pytest.fixture
def policy_factory(db):
    def factory(**values):
        defaults = {"readable_fields": [], "writable_fields": []}
        defaults.update(values)
        return PoliticaIntegracao.objects.create(**defaults)
    return factory
```

```python
def test_scl_master_rejects_external_write(policy_factory, integration):
    policy_factory(integration=integration, resource="client", mode="scl_master")
    with pytest.raises(IntegrationPermissionDenied):
        authorize_fields(integration, resource="client", operation="write", fields={"nome"})


def test_shared_rejects_unlisted_field(policy_factory, integration):
    policy_factory(integration=integration, resource="client", mode="shared", writable_fields=["nome"])
    with pytest.raises(IntegrationPermissionDenied):
        authorize_fields(integration, resource="client", operation="write", fields={"bloqueado"})
```

Also test one owner per internal object, explicit ownership transfer and portal writes: fields controlled by `LEGACY_MASTER` are rejected server-side, `SCL_MASTER` remains editable by authorized portal roles, and `SHARED` portal updates advance the version used by ETags.

- [ ] **Step 2: Verify policy tests fail**

Run: `SECRET_KEY=test-only-key python -m pytest integracoes/tests/test_policies.py integracoes/tests/test_references.py -v`

Expected: missing models/services.

- [ ] **Step 3: Implement policy and request models**

Use enums:

```python
class AuthorityMode(models.TextChoices):
    SCL_MASTER = "scl_master", "SCL"
    LEGACY_MASTER = "legacy_master", "Legado"
    SHARED = "shared", "Compartilhado"
```

Store readable/writable field lists as JSON arrays. Unique `(integracao, recurso)`.

`RequisicaoIntegracao` stores request ID, idempotency key, method, endpoint, payload hash, sanitized response snapshot, counts, HTTP status, timing, IP and normalized error.

- [ ] **Step 4: Implement concrete references**

Create `ClienteReferenciaExterna`, `AssinaturaReferenciaExterna`, `CobrancaReferenciaExterna`, `PagamentoReferenciaExterna` using an abstract base. Each has integration, external ID, internal FK, owner flag, external version and timestamps.

Enforce unique `(integracao, external_id)` and a conditional unique owner per internal FK. `transferir_propriedade_referencia` locks old/new references and related `RequisicaoIntegracao` rows, rejects transfer while either integration has an in-flight request for that resource, requires reason and writes `EventoAuditoria` in the same transaction. Concurrency tests prove no request can write under stale ownership.

- [ ] **Step 5: Implement billing ownership**

`AssinaturaOrigemCobranca` is a one-to-one relation between subscription and integration. Absence means SCL-owned generation. `trocar_origem_cobranca` locks the subscription, origin row and existing competencies; rejects in-flight integration requests or a transition that would duplicate an existing cycle; requires a reason; and writes `EventoAuditoria` atomically. Finance generator tests prove externally controlled subscriptions are skipped under normal and concurrent runs.

- [ ] **Step 6: Enforce authority in portal services and forms**

Create one server-side policy guard used by client, subscription and finance mutation services. Move any remaining direct `ModelForm.save()` mutation behind these services and make portal/API views call them. Forms may render protected fields read-only for usability, but services must reject crafted POSTs that alter fields governed by a `LEGACY_MASTER` owner. Policy/ownership changes are themselves audited.

- [ ] **Step 7: Run model/service tests**

Run: `SECRET_KEY=test-only-key python -m pytest integracoes/tests/test_policies.py integracoes/tests/test_references.py integracoes/tests/test_portal_authority.py integracoes/tests/test_billing_ownership.py -v`

Expected: PASS.

- [ ] **Step 8: Suggested commit**

```bash
git add integracoes licencas/services licencas/forms licencas/views licencas/tests financeiro/forms.py financeiro/views.py financeiro/services/cobrancas.py financeiro/services/pagamentos.py financeiro/tests/test_views.py
git commit -m "feat: model integration authority and external identity"
```

### Task 3: Shared API Infrastructure, ETags, and Idempotency

**Files:**
- Create: `integracoes/api/__init__.py`
- Create: `integracoes/api/authentication.py`
- Create: `integracoes/api/permissions.py`
- Create: `integracoes/api/etag.py`
- Create: `integracoes/api/idempotency.py`
- Create: `integracoes/api/throttles.py`
- Create: `portal/rate_limit.py`
- Modify: `portal/models.py`
- Create: migrations in `portal/migrations/`
- Create: `integracoes/api/exceptions.py`
- Create: `integracoes/api/urls.py`
- Create: `integracoes/tests/test_api_infrastructure.py`
- Modify: `app/urls.py`
- Modify: `app/settings.py`
- Modify: `.env.example`

**Interfaces:**
- Produces: `IntegrationAPIView`, `IntegrationThrottle`, PostgreSQL-backed `consume_rate_limit(scope, key, *, limit, window_seconds)`, `check_if_match(request, instance)` and `idempotent_mutation(request, integration, handler)`.
- Produces: error envelope `{"code": str, "message": str, "details": object}`.

- [ ] **Step 1: Write failing infrastructure tests**

Cover missing/invalid token `401`, missing scope `403`, expired credential, denied CIDR, per-integration and per-origin `429`, stale ETag `409 VERSION_CONFLICT`, same idempotency key/same hash replaying original response, and same key/different hash returning `409 IDEMPOTENCY_CONFLICT`.

- [ ] **Step 2: Verify tests fail**

Run: `SECRET_KEY=test-only-key python -m pytest integracoes/tests/test_api_infrastructure.py -v`

Expected: imports/routes missing.

- [ ] **Step 3: Implement deterministic version tokens**

```python
def version_for(instance):
    raw = f"{instance._meta.label_lower}:{instance.pk}:{instance.alterado_em.isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()
```

Return it quoted in `ETag`. Require `If-Match` only for `SHARED` updates.

- [ ] **Step 4: Implement idempotent mutation storage**

Hash canonical JSON plus method/endpoint. Lock or create `RequisicaoIntegracao` under transaction. Completed same-hash requests replay the stored sanitized status/body; processing duplicates return `409 REQUEST_IN_PROGRESS`.

- [ ] **Step 5: Add integration URL namespace**

Mount at `path("api/v1/integrations/", include((..., "integrations"), namespace="integrations"))`.

Implement a process-shared atomic limiter in PostgreSQL, not Django's per-process/local-memory cache. `JanelaRateLimit` stores unique `(scope, key_hash, window_start)` and an atomic count; `consume_rate_limit` uses row locking/upsert, hashes identifiers and opportunistically deletes expired buckets. Define `limite_requisicoes` as requests per minute, integer range 1-10000. Use `SCL_INTEGRATION_ORIGIN_RATE` (default `300/min`) for origins and `SCL_TRUSTED_PROXY_CIDRS` (default empty) when deriving client IP; never trust forwarded headers from addresses outside that list. Add both names to settings and `.env.example`. In `IntegrationAPIView.initial`, enforce the origin limit and CIDR before authentication, then enforce the integration limit after authentication. Tests cover invalid credentials and concurrent requests through separate database connections so multiple Gunicorn workers cannot bypass either limit.

- [ ] **Step 6: Run infrastructure tests**

Run: `SECRET_KEY=test-only-key python -m pytest integracoes/tests/test_api_infrastructure.py -v`

Expected: PASS.

- [ ] **Step 7: Suggested commit**

```bash
git add integracoes/api integracoes/tests/test_api_infrastructure.py portal/rate_limit.py portal/models.py portal/migrations app/urls.py app/settings.py .env.example
git commit -m "feat: add integration api safeguards"
```

### Task 4: Client and Subscription Integration Endpoints

**Files:**
- Create: `integracoes/api/serializers_clientes.py`
- Create: `integracoes/api/serializers_assinaturas.py`
- Create: `integracoes/api/views_clientes.py`
- Create: `integracoes/api/views_assinaturas.py`
- Modify: `integracoes/api/urls.py`
- Create: `integracoes/tests/test_client_api.py`
- Create: `integracoes/tests/test_subscription_api.py`

**Interfaces:**
- Produces: individual and batch endpoints from spec for clients/subscriptions.
- Consumes: `licencas` forms/validators/services, policy/reference/idempotency infrastructure.

- [ ] **Step 1: Write API contract tests**

Cover cursor pagination; filters by `external_id`, normalized document, state and `updated_since`; read by external ID; POST create; duplicate POST `409`; PATCH; SCL master `403`; shared stale ETag `409`; blocked field rejection; inactive records remaining visible; `updated_at`/version in every response; and batch upsert with one valid/one invalid item.

- [ ] **Step 2: Verify contract tests fail**

Run: `SECRET_KEY=test-only-key python -m pytest integracoes/tests/test_client_api.py integracoes/tests/test_subscription_api.py -v`

Expected: endpoints missing.

- [ ] **Step 3: Implement explicit serializers**

Do not use `fields = "__all__"`. Expose only approved domain fields plus:

```python
external_id = serializers.CharField(max_length=128)
internal_id = serializers.IntegerField(source="pk", read_only=True)
version = serializers.SerializerMethodField()
updated_at = serializers.DateTimeField(source="alterado_em", read_only=True)
```

- [ ] **Step 4: Implement service-backed views**

Views authorize requested fields, resolve references and call the same services used by portal. The domain mutation, external-reference create/update and idempotency completion must occur inside the same per-item `transaction.atomic()`; a crash cannot commit an internal object without its external identity.

- [ ] **Step 5: Implement batches with per-item atomic blocks**

Limit request list length before processing. Each item runs inside its own `transaction.atomic()` and returns `created`, `updated` or `rejected` with code/message.

- [ ] **Step 6: Run client/subscription tests**

Run: `SECRET_KEY=test-only-key python -m pytest integracoes/tests/test_client_api.py integracoes/tests/test_subscription_api.py -v`

Expected: PASS.

- [ ] **Step 7: Suggested commit**

```bash
git add integracoes/api integracoes/tests
git commit -m "feat: sync clients and subscriptions through api"
```

### Task 5: Charge, Payment, and Reversal Endpoints

**Files:**
- Create: `integracoes/api/serializers_financeiro.py`
- Create: `integracoes/api/views_financeiro.py`
- Create: `integracoes/services/financeiro.py`
- Modify: `integracoes/api/urls.py`
- Create: `integracoes/tests/test_finance_api.py`
- Modify: `financeiro/services/pagamentos.py`
- Modify: `financeiro/models.py`
- Create: migrations in `financeiro/migrations/`

**Interfaces:**
- Produces: charge/payment individual, batch and reversal endpoints.
- Produces: `registrar_pagamento_legado(...)` and `estornar_pagamento_legado(...)`.

- [ ] **Step 1: Write financial ownership tests**

Cover cursor-paginated charge/payment lists; filters by `external_id`, state, `updated_since`, subscription, competence and due date; canceled/reversed rows remaining visible with `updated_at`/version; external charge only for externally owned subscription; duplicate competence rejection; PATCH charge cancellation; immediate balance update; integration reversing its own payment; and `403` when reversing manual/gateway/other integration payment.

- [ ] **Step 2: Verify financial API tests fail**

Run: `SECRET_KEY=test-only-key python -m pytest integracoes/tests/test_finance_api.py -v`

Expected: endpoints/services missing.

- [ ] **Step 3: Implement external charge service**

Validate ownership, amount, due date, grace snapshot and unique cycle. Set `origem="legacy"`; create `CobrancaReferenciaExterna` in the same transaction.

- [ ] **Step 4: Implement legacy payment/reversal services**

Add nullable `Pagamento.integracao` with `PROTECT`; legacy-origin rows require it, and `(integracao, identificador_externo)` is unique for legacy payments. Lock charge/payment, enforce positive amount and remaining balance, set `origem="legacy"`, create payment reference in the same transaction, and verify reference ownership before reversal. Confirmation, cancellation and reversal append sanitized `EventoAuditoria` rows atomically.

- [ ] **Step 5: Implement views and batches**

Implement every endpoint in spec section 10.2. Require `Idempotency-Key` for individual charge/payment/reversal and charge cancellation. Batch request key protects the envelope; each `external_id` protects the item. List endpoints use cursor pagination and the approved incremental filters.

- [ ] **Step 6: Prove license-facing financial state changes immediately**

Test `obter_posicao_financeira()` before payment, after payment and after reversal in the same integration test.

- [ ] **Step 7: Run financial integration tests**

Run: `SECRET_KEY=test-only-key python -m pytest integracoes/tests/test_finance_api.py financeiro/tests/test_financial_position.py -v`

Expected: PASS.

- [ ] **Step 8: Suggested commit**

```bash
git add integracoes financeiro/models.py financeiro/migrations financeiro/services/pagamentos.py
git commit -m "feat: sync charges and legacy payments"
```

### Task 6: Integration Administration Portal and Full Gate

**Files:**
- Create: `integracoes/forms.py`
- Create: `integracoes/views.py`
- Create: `integracoes/urls.py`
- Create: `integracoes/templates/integracoes/list.html`
- Create: `integracoes/templates/integracoes/form.html`
- Create: `integracoes/templates/integracoes/detail.html`
- Create: `integracoes/templates/integracoes/rotate_secret.html`
- Create: `integracoes/tests/test_portal.py`
- Modify: `templates/partials/_sidebar.html`
- Modify: `portal/management/commands/sync_roles.py`
- Modify: `app/urls.py`

**Interfaces:**
- Produces: Administrator-only UI for integrations, scopes, policies, credentials, ownership and request audit.

- [ ] **Step 1: Write portal security tests**

Assert only Administrator/superuser can create, rotate, revoke or change policies; CSRF is enforced on every mutation; raw client secret is shown exactly once; existing secret never appears in HTML/logs/audit; credential and policy changes create durable audit events; Consulta can read sanitized audit only if granted.

- [ ] **Step 2: Verify tests fail**

Run: `SECRET_KEY=test-only-key python -m pytest integracoes/tests/test_portal.py -v`

Expected: routes missing.

- [ ] **Step 3: Implement credential lifecycle**

Generate 256-bit secrets with `secrets.token_urlsafe(32)`, store through OAuth Toolkit's supported hashed-secret behavior, display once, and rotate by replacing the Application secret under transaction while invalidating active tokens when revoked.

- [ ] **Step 4: Implement policies and audit views**

Forms whitelist resources, modes and model field names. Audit detail masks document, IP according to role and never renders request authorization headers or secrets.

- [ ] **Step 5: Run complete integration gate**

Run: `SECRET_KEY=test-only-key python -m pytest integracoes financeiro/tests/test_financial_position.py -v`

Expected: PASS.

Run: `SECRET_KEY=test-only-key python manage.py check`

Expected: no issues.

- [ ] **Step 6: Suggested commit**

```bash
git add integracoes templates/partials/_sidebar.html portal/management/commands/sync_roles.py app/urls.py
git commit -m "feat: add legacy integration administration"
```
