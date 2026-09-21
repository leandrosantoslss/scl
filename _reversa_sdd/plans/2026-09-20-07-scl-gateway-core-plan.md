# SCL Gateway Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar o contrato comum, emissão, cancelamento e processamento idempotente de webhooks para gateways financeiros.

**Architecture:** Adaptadores implementam um Protocol independente do ORM. Services convertem modelos em comandos imutáveis, executam o adaptador e persistem resultados transacionalmente. Testes usam um adaptador fake; Efí, Sicredi e Sicoob recebem specs e planos próprios.

**Tech Stack:** Django, Python Protocol/dataclasses, PostgreSQL, DRF, pytest-django, httpx nos adaptadores futuros.

**Spec:** `_reversa_sdd/specs/2026-09-20-scl-licenciamento-financeiro-design.md`

## Global Constraints

- Uma cobrança pode ter somente uma emissão externa ativa.
- Troca de conta/provedor exige cancelamento ou invalidação comprovada da emissão anterior.
- Chaves idempotentes não podem ser reutilizadas com payload diferente.
- Apenas boleto/PIX habilitados na conta podem ser emitidos.
- Webhook é autenticado/verificado pelo adaptador antes de qualquer mutação.
- Evento repetido não cria pagamento duplicado.
- Nenhum adaptador recebe o model Django ou acesso direto ao banco.
- Commits somente com autorização.

---

### Task 1: Adapter Protocol and Contract Suite

**Files:**
- Create: `financeiro/gateways/__init__.py`
- Create: `financeiro/gateways/base.py`
- Create: `financeiro/gateways/registry.py`
- Create: `financeiro/gateways/fake.py`
- Create: `financeiro/tests/gateways/__init__.py`
- Create: `financeiro/tests/gateways/contract.py`
- Create: `financeiro/tests/gateways/test_fake.py`

**Interfaces:**
- Produces: `GatewayAdapter` Protocol.
- Produces: dataclasses `GatewayAccountConfig`, `IssueCommand`, `IssueResult`, `QueryResult`, `CancelResult`, `WebhookEvent`.
- Produces: `register_adapter(provider, factory)` and `get_adapter(account)`.

- [ ] **Step 1: Write the reusable contract tests**

The contract must assert:

```python
def assert_gateway_contract(adapter, command):
    result = adapter.issue(command)
    assert result.external_id
    assert result.status == "issued"
    assert bool(result.digitable_line) ^ bool(result.pix_copy_paste) or result.hybrid

    queried = adapter.query(result.external_id)
    assert queried.external_id == result.external_id

    cancelled = adapter.cancel(result.external_id, idempotency_key="cancel-1")
    assert cancelled.status == "cancelled"
```

Also cover duplicate issue/cancel keys, unsupported method, timeout mapped to `GatewayTemporaryError`, invalid credentials mapped to `GatewayAuthenticationError`, and validation errors.

- [ ] **Step 2: Verify contract tests fail**

Run: `SECRET_KEY=test-only-key python -m pytest financeiro/tests/gateways/test_fake.py -v`

Expected: gateway package missing.

- [ ] **Step 3: Define immutable adapter types**

```python
class GatewayAdapter(Protocol):
    def validate_config(self) -> None: ...
    def test_connection(self) -> None: ...
    def is_presentation_url_allowed(self, url: str) -> bool: ...
    def issue(self, command: IssueCommand) -> IssueResult: ...
    def query(self, external_id: str) -> QueryResult: ...
    def cancel(self, external_id: str, *, idempotency_key: str) -> CancelResult: ...
    def parse_webhook(self, *, headers: Mapping[str, str], body: bytes) -> WebhookEvent: ...
```

`IssueCommand` carries internal charge UUID/ID, amount, due date, payer document/name/address, method and idempotency key. It carries no ORM object.

Define `IssueResult` exactly with `external_id`, normalized `status`, `method`, optional `digitable_line`, `pix_copy_paste`, `pix_qr_text`, `presentation_url`, and `hybrid: bool`. `QueryResult` includes external ID/status, paid/canceled timestamps and amount; `CancelResult` includes external ID/status; `WebhookEvent` includes provider, external event/reference IDs, normalized type/status, amount and occurred-at. Contract tests exercise `hybrid` and URL allow/deny behavior.

- [ ] **Step 4: Implement registry and FakeAdapter**

Registry rejects duplicate provider registration and unknown providers. Fake adapter stores calls in memory and implements deterministic responses for tests only.

- [ ] **Step 5: Run contract tests**

Run: `SECRET_KEY=test-only-key python -m pytest financeiro/tests/gateways/test_fake.py -v`

Expected: PASS.

- [ ] **Step 6: Suggested commit**

```bash
git add financeiro/gateways financeiro/tests/gateways
git commit -m "feat: define financial gateway contract"
```

### Task 2: Transactional Emission and Cancellation Services

**Files:**
- Create: `financeiro/services/emissoes.py`
- Create: `financeiro/management/commands/reconciliar_emissoes.py`
- Create: `financeiro/tests/test_emissao_service.py`
- Create: `financeiro/tests/test_reconciliacao_gateway.py`

**Interfaces:**
- Produces: `emitir_cobranca(cobranca, *, conta, meio, idempotency_key, usuario) -> EmissaoCobranca`.
- Produces: `cancelar_emissao(emissao, *, idempotency_key, usuario) -> EmissaoCobranca`.
- Produces: `testar_conexao_conta(conta, *, usuario) -> ConnectionTestResult`.
- Produces: `reconciliar_emissao(emissao, *, motivo) -> EmissaoCobranca` and idempotent `reconciliar_emissoes` command.
- Consumes: adapter registry and finance models.

- [ ] **Step 1: Write failing service tests**

Cover inactive account, method disabled, canceled/paid charge, duplicate same-key replay, different payload conflict, one active emission, definitive adapter failure persisted as failed, ambiguous timeout persisted as `pending/unknown`, cancellation, safe reissue on another account only after cancellation or reconciled non-creation, sanitized connection tests, and query reconciliation for missing/insufficient/uncertain/out-of-order webhook state.

- [ ] **Step 2: Verify tests fail**

Run: `SECRET_KEY=test-only-key python -m pytest financeiro/tests/test_emissao_service.py financeiro/tests/test_reconciliacao_gateway.py -v`

Expected: service missing.

- [ ] **Step 3: Build IssueCommand without leaking ORM**

Map payer data explicitly and normalize document. Reject missing provider-required data as domain validation before network access.

- [ ] **Step 4: Implement two-phase persistence safely**

1. Under transaction and row lock, validate charge/account and create `requested` emission with unique idempotency key.
2. Call adapter outside the database lock.
3. Under a new transaction and lock, persist issued/failed result if request still owns the operation.

This avoids holding a database transaction open during network I/O while preventing duplicate active emissions. A timeout/connection loss after request dispatch is not a definitive failure: persist `pending/unknown`, retain the active-emission guard and require `query()` reconciliation by idempotency/external reference before retry or reissue. Only provider-confirmed rejection may become failed immediately.

- [ ] **Step 5: Implement cancellation with the same pattern**

Only issued/active emissions can cancel. Persist gateway result; do not mark canceled locally when provider returns unknown/temporary failure.

`testar_conexao_conta` calls the adapter without holding a database lock, then persists status/timestamp/normalized error and a sanitized `EventoAuditoria`. `reconciliar_emissao` queries the provider, locks emission/charge before applying a newer normalized state, creates at most one payment, never rolls a paid state backward, and leaves uncertain/temporary failures pending for retry. The command uses `--limit`, `--older-than-minutes` and exits non-zero when rows remain in error.

- [ ] **Step 6: Run service tests**

Run: `SECRET_KEY=test-only-key python -m pytest financeiro/tests/test_emissao_service.py financeiro/tests/test_reconciliacao_gateway.py -v`

Expected: PASS.

- [ ] **Step 7: Suggested commit**

```bash
git add financeiro/services/emissoes.py financeiro/management/commands/reconciliar_emissoes.py financeiro/tests/test_emissao_service.py financeiro/tests/test_reconciliacao_gateway.py
git commit -m "feat: issue and cancel external charges safely"
```

### Task 3: Webhook Routing and Idempotent Payment

**Files:**
- Create: `financeiro/api/__init__.py`
- Create: `financeiro/api/webhooks.py`
- Create: `financeiro/api/urls.py`
- Create: `financeiro/services/webhooks.py`
- Create: `financeiro/tests/test_gateway_webhooks.py`
- Modify: `financeiro/services/pagamentos.py`
- Modify: `app/urls.py`

**Interfaces:**
- Produces: `POST /api/v1/payments/webhooks/<provider>/<account_public_id>/`.
- Produces: `processar_evento_gateway(account, event) -> EventoGateway`.

- [ ] **Step 1: Write failing webhook tests**

Cover unknown/inactive account, provider/account mismatch, invalid signature, paid event, duplicate event routed through another account, payment greater than remaining balance, out-of-order cancellation after paid, insufficient/uncertain event triggering provider reconciliation, temporary query failure preserving retry state, and no secret/body leakage in response/log.

- [ ] **Step 2: Verify tests fail**

Run: `SECRET_KEY=test-only-key python -m pytest financeiro/tests/test_gateway_webhooks.py -v`

Expected: route/service missing.

- [ ] **Step 3: Implement raw-body verification flow**

The view resolves provider/account, reads raw bytes once, calls `adapter.parse_webhook(headers, body)`, then invokes the service. Do not parse JSON before signature verification when the provider signs raw bytes.

- [ ] **Step 4: Implement event idempotency**

Unique `(provider, external_event_id)`. Lock event/emission/charge. A confirmed payment calls a gateway-specific payment service with external event ID. Repeated event returns the original successful outcome even if routed through another account URL. When the verified event is insufficient or conflicts with durable state, call `reconciliar_emissao` before applying a financial mutation.

- [ ] **Step 5: Define safe HTTP acknowledgements**

Return `2xx` only after durable event acceptance. Invalid signature returns `401/403`; unknown reference returns provider-compatible non-2xx so retries remain possible; internal temporary failures return `503`.

- [ ] **Step 6: Run webhook tests**

Run: `SECRET_KEY=test-only-key python -m pytest financeiro/tests/test_gateway_webhooks.py -v`

Expected: PASS.

- [ ] **Step 7: Suggested commit**

```bash
git add financeiro/api financeiro/services/webhooks.py financeiro/services/pagamentos.py financeiro/tests/test_gateway_webhooks.py app/urls.py
git commit -m "feat: process gateway webhooks idempotently"
```

### Task 4: Emission Portal Workflow

**Files:**
- Modify: `financeiro/forms.py`
- Modify: `financeiro/views.py`
- Modify: `financeiro/urls.py`
- Create: `financeiro/templates/financeiro/emissoes/form.html`
- Create: `financeiro/templates/financeiro/emissoes/detail.html`
- Create: `financeiro/templates/financeiro/emissoes/cancel.html`
- Create: `financeiro/tests/test_emissao_views.py`

**Interfaces:**
- Produces: Financeiro/Admin actions to choose account/method, issue, inspect and cancel.

- [ ] **Step 1: Write failing portal workflow tests**

Assert available accounts filtered by active/method, no secret fields rendered, CSRF-enforced POST-only issue/cancel/connection-test/reconciliation, role enforcement, connection status persisted without secret leakage, failed attempt visible with normalized error, and successful boleto/PIX data visible.

- [ ] **Step 2: Verify tests fail**

Run: `SECRET_KEY=test-only-key python -m pytest financeiro/tests/test_emissao_views.py -v`

Expected: routes/templates missing.

- [ ] **Step 3: Implement forms and service-backed views**

Generate a server-side idempotency key per confirmation form and keep it in a signed hidden field/session. Never accept gateway credentials or arbitrary external IDs from this form.

- [ ] **Step 4: Render method-specific output safely**

Escape provider text. Render `presentation_url` only when HTTPS and `adapter.is_presentation_url_allowed(url)` is true; otherwise suppress it and record a normalized validation error. Render PIX copy-and-paste as text and QR generated locally from that text, not remote HTML.

- [ ] **Step 5: Run gateway core gate**

Run: `SECRET_KEY=test-only-key python -m pytest financeiro/tests/gateways financeiro/tests/test_emissao_service.py financeiro/tests/test_reconciliacao_gateway.py financeiro/tests/test_gateway_webhooks.py financeiro/tests/test_emissao_views.py -v`

Expected: PASS with FakeAdapter.

- [ ] **Step 6: Suggested commit**

```bash
git add financeiro/forms.py financeiro/views.py financeiro/urls.py financeiro/templates/financeiro/emissoes financeiro/tests/test_emissao_views.py
git commit -m "feat: add external charge emission workflow"
```

### Task 5: Provider Specification Gate

**Files:**
- Create: `_reversa_sdd/specs/gateways/efi.md`
- Create: `_reversa_sdd/specs/gateways/sicredi.md`
- Create: `_reversa_sdd/specs/gateways/sicoob.md`
- Create: `_reversa_sdd/specs/gateways/contract-matrix.md`

**Interfaces:**
- Produces: approved provider-specific contracts required before adapter plans.

- [ ] **Step 1: Collect official evidence for each contracted product**

For each provider, record official documentation version/URL, homologation and production base URLs, OAuth/mTLS requirements, certificate formats, boleto endpoints, PIX endpoints, idempotency support, webhook signing, retry policy, status mapping, cancellation behavior and rate limits.

- [ ] **Step 2: Verify contracted capabilities with real account metadata**

Record whether each account contract enables boleto, PIX or hybrid, and which identifiers (cooperative, account, agreement, beneficiary, Pix key) are required. Do not put secrets or certificates in specs.

- [ ] **Step 3: Complete the contract matrix**

Every `GatewayAdapter` method must map to a documented provider operation or an explicit unsupported capability. The first release acceptance requires issue/query/cancel/webhook/payment for every method enabled on each contracted account, whether boleto, PIX or both.

- [ ] **Step 4: Obtain user approval for all three provider specs**

Do not write provider adapter code before the relevant spec is approved. After approval, create one writing-plans document per provider with exact endpoints, payloads, error maps and sandbox tests.

- [ ] **Step 5: Record the gate**

Update `_reversa_sdd/analysis-scl/progress.md` with documentation versions, account capabilities and approval status. No Git commit is required for external secrets; the four non-secret spec files may be committed only with authorization.
