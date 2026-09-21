# SCL Licensing API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar decisão diária de licença, API autenticada, auditoria e token RS256 verificável offline.

**Architecture:** Criar o app `licenciamento`. Uma única service class aplica a precedência cliente/sistema/assinatura/financeiro; a API apenas autentica, valida entrada, chama o serviço, emite token quando permitido e registra auditoria.

**Tech Stack:** Django REST Framework, PyJWT, cryptography, PostgreSQL, pytest-django.

**Spec:** `_reversa_sdd/specs/2026-09-20-scl-licenciamento-financeiro-design.md`

## Global Constraints

- Nunca usar MD5.
- Credencial identifica o sistema e é independente de OAuth2 das integrações.
- Resultado de negócio usa HTTP 200; falha técnica/autenticação usa status HTTP apropriado.
- Token usa RS256, `kid`, `iss`, `aud`, `sub`, `subscription_id`, `decision`, `iat`, `exp`, `jti`.
- Token expira no início do próximo dia em `America/Sao_Paulo`.
- Bloqueio após emissão não invalida o token diário já entregue.
- Token completo e segredo nunca são persistidos/logados.
- Commits somente com autorização.

---

### Task 1: Licensing Models

**Files:**
- Modify: `requirements.txt`
- Create: `licenciamento/__init__.py`
- Create: `licenciamento/apps.py`
- Create: `licenciamento/models.py`
- Create: `licenciamento/migrations/__init__.py`
- Create: `licenciamento/tests/__init__.py`
- Create: `licenciamento/tests/conftest.py`
- Create: `licenciamento/tests/test_models.py`
- Modify: `app/settings.py`
- Modify: `app/admin.py`

**Interfaces:**
- Produces: `CredencialSistema`, `ConsultaLicenca`, `TokenLicenca`.

- [ ] **Step 1: Add JWT dependency**

Add `PyJWT[crypto]>=2.10,<3`.

- [ ] **Step 2: Write failing model tests**

Create the system fixture:

```python
import pytest

from licencas.models import Sistema


@pytest.fixture
def sistema(db):
    return Sistema.objects.create(nome="ERP", codigo="erp")
```

Then add the model tests:

```python
import pytest
from django.db import IntegrityError

from licenciamento.models import CredencialSistema, TokenLicenca


@pytest.mark.django_db
def test_credential_public_id_is_unique(sistema):
    CredencialSistema.objects.create(sistema=sistema, public_id="client-a", secret_hash="x")
    with pytest.raises(IntegrityError):
        CredencialSistema.objects.create(sistema=sistema, public_id="client-a", secret_hash="y")


def test_token_string_is_not_a_model_field():
    field_names = {field.name for field in TokenLicenca._meta.fields}
    assert "token" not in field_names
    assert "token_hash" in field_names
```

- [ ] **Step 3: Verify tests fail**

Run: `SECRET_KEY=test-only-key python -m pytest licenciamento/tests/test_models.py -v`

Expected: app/model missing.

- [ ] **Step 4: Implement models**

`CredencialSistema`: system FK, unique public ID, Django password hash, active, expiry, last use, revoked timestamp, audit timestamps.

`ConsultaLicenca`: UUID request ID, credential/system/client/subscription nullable FKs, document HMAC hash plus masked suffix, app version, installation ID, source IP, decision code, allowed, latency milliseconds and timestamp.

`TokenLicenca`: unique JTI, client/system/subscription FKs, SHA-256 token hash, kid, issue/expiry/revocation timestamps and decision code.

- [ ] **Step 5: Migrate and run tests**

Run: `SECRET_KEY=test-only-key DATABASE_URL="$SCL_TEST_DATABASE_URL" python manage.py makemigrations licenciamento`

Run: `SECRET_KEY=test-only-key DATABASE_URL="$SCL_TEST_DATABASE_URL" python manage.py migrate`

Run: `SECRET_KEY=test-only-key python -m pytest licenciamento/tests/test_models.py -v`

Expected: PASS.

- [ ] **Step 6: Suggested commit**

```bash
git add requirements.txt app/settings.py app/admin.py licenciamento
git commit -m "feat: add licensing audit models"
```

### Task 2: System Credential Lifecycle and Authentication

**Files:**
- Create: `licenciamento/services/__init__.py`
- Create: `licenciamento/services/credentials.py`
- Create: `licenciamento/api/__init__.py`
- Create: `licenciamento/api/authentication.py`
- Create: `licenciamento/tests/test_credentials.py`

**Interfaces:**
- Produces: `create_credential(system, *, user) -> (CredencialSistema, raw_token)`.
- Produces: `rotate_credential(credential, *, user) -> (CredencialSistema, raw_token)` and `retire_credential(credential, *, user, reason)`.
- Produces: DRF `SystemCredentialAuthentication`.
- Credential wire format: `<public_id>.<random_secret>`.

- [ ] **Step 1: Write failing credential tests**

Cover raw secret shown only on creation/rotation, stored hash not equal raw token, valid authentication, revoked/expired/inactive credential rejection, system mismatch rejection, `last_used_at` update, old/new credentials both valid during rotation overlap, and old credential rejection only after explicit retirement.

- [ ] **Step 2: Verify tests fail**

Run: `SECRET_KEY=test-only-key python -m pytest licenciamento/tests/test_credentials.py -v`

Expected: services/authentication missing.

- [ ] **Step 3: Implement secure token creation**

```python
raw_secret = secrets.token_urlsafe(32)
public_id = secrets.token_urlsafe(12)
wire_token = f"{public_id}.{raw_secret}"
secret_hash = make_password(raw_secret)
```

Lookup by public ID, verify with `check_password`, and use `hmac.compare_digest` where direct comparison is needed.

Rotation creates a distinct active `CredencialSistema` for the same system and never overwrites or auto-revokes the current row. Explicit retirement requires confirmation/reason, sets revocation fields, and records a sanitized `EventoAuditoria`; creation and rotation are audited in the same transaction without storing the raw secret.

- [ ] **Step 4: Implement DRF authentication**

Parse `Authorization: Bearer <wire_token>`. Return an immutable principal containing credential and system; never set a human Django user. Generic 401 messages must not reveal whether public ID or secret was wrong.

- [ ] **Step 5: Run credential tests**

Run: `SECRET_KEY=test-only-key python -m pytest licenciamento/tests/test_credentials.py -v`

Expected: PASS.

- [ ] **Step 6: Suggested commit**

```bash
git add licenciamento/services/credentials.py licenciamento/api/authentication.py licenciamento/tests/test_credentials.py
git commit -m "feat: authenticate licensed systems securely"
```

### Task 3: Central License Decision Service

**Files:**
- Create: `licenciamento/services/decisions.py`
- Create: `licenciamento/tests/test_decisions.py`

**Interfaces:**
- Produces: `LicenseDecision(code, allowed, message, next_due_date, oldest_overdue_date, grace_ends_on)`.
- Produces: `decide_license(*, system, document, today) -> tuple[LicenseDecision, Cliente | None, ClienteSistema | None]`.

- [ ] **Step 1: Write precedence table tests**

Use parameterized scenarios in this exact order:

```text
SYSTEM_INACTIVE
CLIENT_NOT_FOUND
CLIENT_INACTIVE
CLIENT_BLOCKED
SUBSCRIPTION_NOT_FOUND
SUBSCRIPTION_NOT_STARTED
SUBSCRIPTION_EXPIRED
SUBSCRIPTION_INACTIVE
SUBSCRIPTION_BLOCKED
DELINQUENT
OVERDUE_IN_GRACE
ACTIVE
```

Assert manual states beat financial state and oldest outstanding charge supplies dates.

- [ ] **Step 2: Verify decision tests fail**

Run: `SECRET_KEY=test-only-key python -m pytest licenciamento/tests/test_decisions.py -v`

Expected: service missing.

- [ ] **Step 3: Implement immutable decision type**

```python
@dataclass(frozen=True)
class LicenseDecision:
    code: str
    allowed: bool
    message: str
    next_due_date: date | None = None
    oldest_overdue_date: date | None = None
    grace_ends_on: date | None = None
```

- [ ] **Step 4: Implement ordered decision logic**

Normalize/validate document, use `select_related`, check dates using the injected `today`, then call `financeiro.selectors.obter_posicao_financeira`. Do not catch unexpected database errors as business denials.

- [ ] **Step 5: Run decision tests**

Run: `SECRET_KEY=test-only-key python -m pytest licenciamento/tests/test_decisions.py financeiro/tests/test_financial_position.py -v`

Expected: PASS.

- [ ] **Step 6: Suggested commit**

```bash
git add licenciamento/services/decisions.py licenciamento/tests/test_decisions.py
git commit -m "feat: centralize license decisions"
```

### Task 4: RS256 Daily License Tokens

**Files:**
- Create: `licenciamento/services/tokens.py`
- Create: `licenciamento/tests/test_tokens.py`
- Modify: `app/settings.py`
- Modify: `.env.example`

**Interfaces:**
- Produces: `issue_license_token(*, client, system, subscription, decision, now) -> IssuedToken`.
- Produces: `verify_license_token(token, *, expected_system_code, now) -> dict` for server-side tests/support.
- Settings: `SCL_LICENSE_ISSUER`, `SCL_LICENSE_ACTIVE_KID`, `SCL_LICENSE_PRIVATE_KEY`, `SCL_LICENSE_PUBLIC_KEYS_JSON`.

- [ ] **Step 1: Write failing cryptographic tests**

Cover required claims, RS256 algorithm, correct audience, tampered payload, wrong audience, old/new public key during rotation, expiry at next São Paulo midnight, and raw token absent from database.

- [ ] **Step 2: Verify tests fail**

Run: `SECRET_KEY=test-only-key python -m pytest licenciamento/tests/test_tokens.py -v`

Expected: token service/settings missing.

- [ ] **Step 3: Implement next-midnight calculation**

```python
def next_operational_midnight(now):
    zone = ZoneInfo("America/Sao_Paulo")
    local_now = now.astimezone(zone)
    next_day = local_now.date() + timedelta(days=1)
    return datetime.combine(next_day, time.min, tzinfo=zone).astimezone(timezone.utc)
```

- [ ] **Step 4: Implement RS256 issue and verify**

Use PyJWT with explicit `algorithms=["RS256"]`; never accept algorithm from payload. Header includes active `kid`. Persist SHA-256 token hash/JTI/metadata after successful encoding.

- [ ] **Step 5: Add safe environment documentation**

`.env.example` contains variable names and generation commands, not real keys:

```text
# openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072
SCL_LICENSE_ISSUER=scl
SCL_LICENSE_ACTIVE_KID=primary-2026
SCL_LICENSE_PRIVATE_KEY=
SCL_LICENSE_PUBLIC_KEYS_JSON={}
```

- [ ] **Step 6: Run token tests**

Run: `SECRET_KEY=test-only-key python -m pytest licenciamento/tests/test_tokens.py -v`

Expected: PASS using test-generated RSA keys.

- [ ] **Step 7: Suggested commit**

```bash
git add licenciamento/services/tokens.py licenciamento/tests/test_tokens.py app/settings.py .env.example
git commit -m "feat: issue daily rs256 license tokens"
```

### Task 5: License Check API, Throttling, and Audit

**Files:**
- Create: `licenciamento/api/serializers.py`
- Create: `licenciamento/api/throttles.py`
- Create: `licenciamento/api/views.py`
- Create: `licenciamento/api/urls.py`
- Create: `licenciamento/tests/test_api.py`
- Modify: `app/urls.py`
- Modify: `app/settings.py`
- Modify: `.env.example`
- Modify: `requirements.txt`
- Modify: `pytest.ini`

**Interfaces:**
- Produces: `POST /api/v1/licenses/check`.
- Request fields: `system_code`, `document`, optional `installation_id`, optional `app_version`.
- Response fields follow spec section 9.
- Consumes: PostgreSQL-backed `portal.rate_limit.consume_rate_limit` introduced by Plan 05.

- [ ] **Step 1: Write endpoint contract tests**

Cover `400`, `401`, `403`, independent per-credential and per-origin `429`, all business codes as HTTP 200, token only when allowed, credential/system mismatch, audit creation, no raw token/secret in audit, consistent `grace_ends_on` response field, and request ID response header.

- [ ] **Step 2: Verify API tests fail**

Run: `SECRET_KEY=test-only-key python -m pytest licenciamento/tests/test_api.py -v`

Expected: route missing.

- [ ] **Step 3: Implement explicit request/response serializers**

Validate and normalize document before service invocation. Messages are response data only; clients must branch on stable `code`.

- [ ] **Step 4: Implement per-credential and per-origin throttles**

Use the shared PostgreSQL atomic limiter with independent hashed keys for credential public ID and normalized source IP. Defaults are `60/min` per credential and `120/min` per origin, configured by `SCL_LICENSE_CREDENTIAL_RATE` and `SCL_LICENSE_ORIGIN_RATE`. Derive IP only through explicitly trusted proxy settings. Override the view's `initial` flow so origin throttling happens before credential authentication, including invalid Bearer tokens; credential throttling follows successful authentication. Concurrency tests use separate database connections to prove multiple Gunicorn workers share both limits.

- [ ] **Step 5: Implement view orchestration and audit**

Measure monotonic latency. Audit in a `finally` path where safe, but do not transform unexpected internal failures into `allowed=false`. Hash document with a dedicated `SCL_AUDIT_HMAC_KEY`, separate from `SECRET_KEY` and JWT keys, and retain only masked suffix for support. Add all three setting names to `.env.example`; startup/check must fail outside tests when the HMAC key is absent. Add `pytest-env>=1.1,<2` and set only `SCL_AUDIT_HMAC_KEY=test-only-audit-hmac-key` in `pytest.ini` so tests never depend on a production secret.

- [ ] **Step 6: Run API and cross-domain tests**

Run: `SECRET_KEY=test-only-key python -m pytest licenciamento financeiro/tests/test_financial_position.py -v`

Expected: PASS.

- [ ] **Step 7: Suggested commit**

```bash
git add licenciamento/api licenciamento/tests/test_api.py app/urls.py app/settings.py .env.example requirements.txt pytest.ini
git commit -m "feat: expose audited license check api"
```

### Task 6: Credential Portal and Consumer Contract

**Files:**
- Create: `licenciamento/forms.py`
- Create: `licenciamento/views.py`
- Create: `licenciamento/urls.py`
- Create: `licenciamento/templates/licenciamento/credentials/list.html`
- Create: `licenciamento/templates/licenciamento/credentials/show_secret.html`
- Create: `licenciamento/templates/licenciamento/checks/list.html`
- Create: `licenciamento/templates/licenciamento/checks/detail.html`
- Create: `licenciamento/tests/test_portal.py`
- Create: `_reversa_sdd/specs/scl-license-consumer-contract.md`
- Modify: `templates/partials/_sidebar.html`
- Modify: `portal/management/commands/sync_roles.py`
- Modify: `app/urls.py`

**Interfaces:**
- Produces: Administrator-only credential lifecycle and sanitized audit views.
- Produces: consumer contract with request, response codes, JWKS/public-key distribution and offline algorithm.

- [ ] **Step 1: Write portal permission and secret tests**

Assert only Administrator/superuser creates/rotates/revokes; CSRF is enforced for each mutation; raw credential shown once; old/new credentials overlap until explicit retirement; audit visible according to role; token hash/JTI visible only to Administrator; no token body rendered.

- [ ] **Step 2: Verify tests fail**

Run: `SECRET_KEY=test-only-key python -m pytest licenciamento/tests/test_portal.py -v`

Expected: routes missing.

- [ ] **Step 3: Implement portal views using credential services**

Never reconstruct or redisplay stored secrets. Rotation creates a new credential row and leaves the previous row valid for a controlled overlap. Retirement is a separate confirmed POST with reason and durable audit event.

- [ ] **Step 4: Write the consumer contract**

Document exact HTTP examples, all stable codes, RS256 verification (`iss`, `aud`, `exp`, `kid`), next-day behavior, five-minute technical clock tolerance without crossing the operational day, and fail-closed behavior after expiry.

- [ ] **Step 5: Run complete licensing gate**

Run: `SECRET_KEY=test-only-key python -m pytest licenciamento -v`

Expected: PASS.

Run: `SECRET_KEY=test-only-key SCL_AUDIT_HMAC_KEY=test-only-audit-hmac-key python manage.py check`

Expected: no issues.

- [ ] **Step 6: Suggested commit**

```bash
git add licenciamento templates/partials/_sidebar.html portal/management/commands/sync_roles.py app/urls.py _reversa_sdd/specs/scl-license-consumer-contract.md
git commit -m "feat: complete licensing administration and contract"
```
