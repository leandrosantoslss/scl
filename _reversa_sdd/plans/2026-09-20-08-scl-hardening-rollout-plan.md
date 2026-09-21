# SCL Hardening and Rollout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preparar o SCL para operação segura, observável e gradual, provando concorrência, desempenho e recuperação.

**Architecture:** Consolidar dashboards e logging estruturado sobre os serviços existentes, endurecer configurações HTTP/containers e executar testes integrados em PostgreSQL. O Admin permanece contingência apenas para superusuários.

**Tech Stack:** Django, PostgreSQL, Gunicorn, WhiteNoise, pytest, Locust, Docker Compose.

**Spec:** `_reversa_sdd/specs/2026-09-20-scl-licenciamento-financeiro-design.md`

## Global Constraints

- Não alterar regras de domínio nesta fase; corrigir somente falhas demonstradas pelos gates.
- Não registrar documentos completos, tokens, segredos, certificados ou payloads financeiros sensíveis.
- Deploy não executa migrações automaticamente no processo web.
- Admin continua em `/admin/`, somente superusuário.
- Rollout é gradual; portal não substitui Admin antes de paridade e observação.
- Commits somente com autorização.

---

### Task 1: Production Dashboard and Query Budgets

**Files:**
- Create: `portal/selectors.py`
- Modify: `portal/views.py`
- Modify: `templates/portal/home.html`
- Create: `portal/tests/test_dashboard_metrics.py`

**Interfaces:**
- Produces: `dashboard_metrics(*, today) -> DashboardMetrics`.
- Metrics: clients by state, subscriptions by system, due in the next 7 operational days, grace/delinquent as of `today`, received value in the current `America/Sao_Paulo` calendar month, 10 most recent confirmed payments, gateway failures in the last 24 hours, integration conflicts in the last 24 hours, and denied license checks since local midnight.

- [ ] **Step 1: Write exact metric and query-count tests**

Seed representative rows and assert every count/value. Wrap dashboard request in `django_assert_num_queries` with a starting budget of 15 queries; lower it if implementation permits.

- [ ] **Step 2: Verify tests fail**

Run: `SECRET_KEY=test-only-key python -m pytest portal/tests/test_dashboard_metrics.py -v`

Expected: missing selector/metrics.

- [ ] **Step 3: Implement aggregated selectors**

Use `Count(..., filter=Q(...))`, `Sum`, `Exists` and bounded recent lists. Do not loop over clients/subscriptions to calculate financial state.

- [ ] **Step 4: Render accessible cards and tables**

Every chart has a textual total/table fallback. Status is conveyed by text plus color. Load ApexCharts only on dashboard and feed data through `json_script`.

- [ ] **Step 5: Run dashboard tests**

Run: `SECRET_KEY=test-only-key python -m pytest portal/tests/test_dashboard_metrics.py -v`

Expected: PASS within query budget.

- [ ] **Step 6: Suggested commit**

```bash
git add portal/selectors.py portal/views.py portal/tests/test_dashboard_metrics.py templates/portal/home.html
git commit -m "feat: add operational dashboard metrics"
```

### Task 2: Structured Logging and Audit Retention

**Files:**
- Modify: `requirements.txt`
- Create: `app/logging.py`
- Modify: `app/settings.py`
- Create: `tests/test_logging.py`
- Create: `licenciamento/management/commands/purge_license_audit.py`
- Create: `integracoes/management/commands/purge_integration_audit.py`
- Modify: `licenciamento/models.py`
- Modify: `integracoes/models.py`
- Create: migrations in `licenciamento/migrations/` and `integracoes/migrations/`
- Create: `tests/test_audit_retention.py`

**Interfaces:**
- Produces: JSON logs with request ID, subsystem, event, outcome, duration; no sensitive fields.
- Produces: retention commands with policy defaults, optional stricter `--before YYYY-MM-DD`, and dry-run default.

- [ ] **Step 1: Add logging dependency and failing redaction tests**

Add `python-json-logger>=3,<4`. Tests emit events containing `authorization`, `token`, `client_secret`, `document` and assert output replaces values with `[REDACTED]` or masked document.

- [ ] **Step 2: Verify tests fail**

Run: `SECRET_KEY=test-only-key python -m pytest tests/test_logging.py -v`

Expected: logging helper missing.

- [ ] **Step 3: Implement a field-allowlist logger adapter**

Allow only known fields such as request ID, integration/account public ID, event type, status, HTTP code, latency and counts. Reject arbitrary dict expansion from external payloads.

- [ ] **Step 4: Implement exact retention and legal-hold rules**

Keep `ConsultaLicenca` for 180 days and `RequisicaoIntegracao` for 365 days. Add nullable `retencao_legal_ate` and `motivo_retencao` to both; a future date or sentinel maximum date excludes the row from purge. Default prints eligible/held counts only. `--execute` requires an explicit confirmation flag and deletes eligible rows in chunks of 1,000. Never purge `EventoAuditoria`, payment/charge ledger, idempotency rows still referenced by the retention window, or any held row. Tests freeze the date and assert exact boundary-day, chunking and legal-hold behavior.

- [ ] **Step 5: Run logging and retention tests**

Run: `SECRET_KEY=test-only-key python -m pytest tests/test_logging.py tests/test_audit_retention.py -v`

Expected: PASS.

- [ ] **Step 6: Suggested commit**

```bash
git add requirements.txt app/logging.py app/settings.py tests licenciamento/models.py licenciamento/migrations licenciamento/management integracoes/models.py integracoes/migrations integracoes/management
git commit -m "feat: add safe operational logging and retention"
```

### Task 3: Production HTTP and Static Security

**Files:**
- Modify: `requirements.txt`
- Modify: `app/settings.py`
- Modify: `Dockerfile`
- Modify: `docker-compose.yml`
- Create: `tests/test_security_settings.py`

**Interfaces:**
- Produces: Gunicorn runtime, WhiteNoise static serving, secure proxy/cookie/HSTS settings controlled by environment.

- [ ] **Step 1: Add runtime dependencies**

Add:

```text
gunicorn>=23,<24
whitenoise>=6.9,<7
```

- [ ] **Step 2: Write failing production settings tests**

Assert production mode enables secure cookies, HSTS, referrer policy, nosniff, proxy SSL header, non-empty allowed hosts and ManifestStaticFilesStorage.

- [ ] **Step 3: Verify tests fail**

Run: `SECRET_KEY=test-only-key DEBUG=false ALLOWED_HOSTS=example.com python -m pytest tests/test_security_settings.py -v`

Expected: missing security settings.

- [ ] **Step 4: Implement environment-driven security**

```python
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=0 if DEBUG else 31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
```

Insert WhiteNoise after SecurityMiddleware and configure compressed manifest storage.

- [ ] **Step 5: Switch container command to Gunicorn**

Use:

```dockerfile
CMD ["gunicorn", "app.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "--access-logfile", "-"]
```

Add a build step with explicit non-production, build-scoped values that do not become runtime secrets:

```dockerfile
RUN SECRET_KEY=build-only-secret-not-used-at-runtime-00000000000000000000 \
    SCL_AUDIT_HMAC_KEY=build-only-audit-key-not-used-at-runtime \
    python manage.py collectstatic --noinput
```

- [ ] **Step 6: Run deployment checks**

Run: `SECRET_KEY="$(openssl rand -base64 48)" DEBUG=false ALLOWED_HOSTS=example.com SECURE_HSTS_SECONDS=31536000 DATABASE_URL="$SCL_TEST_DATABASE_URL" SCL_AUDIT_HMAC_KEY="$(openssl rand -hex 32)" python manage.py check --deploy`

Expected: no security warnings.

Run: `SCL_ENV_FILE=.env.example docker compose config`

Expected: exit 0.

- [ ] **Step 7: Suggested commit**

```bash
git add requirements.txt app/settings.py Dockerfile docker-compose.yml tests/test_security_settings.py
git commit -m "chore: harden production runtime"
```

### Task 4: PostgreSQL Concurrency and Load Gates

**Files:**
- Create: `tests/concurrency/test_charge_generation.py`
- Create: `tests/concurrency/test_payment_races.py`
- Create: `tests/concurrency/test_emission_races.py`
- Create: `tests/concurrency/test_idempotency_races.py`
- Create: `tests/load/license_api.py`
- Create: `tests/load/integration_api.py`
- Create: `tests/load/assert_results.py`
- Modify: `requirements.txt`

**Interfaces:**
- Produces: repeatable concurrency suite requiring PostgreSQL.
- Produces: Locust scenarios for license and integration APIs.

- [ ] **Step 1: Add load-test dependency**

Add `locust>=2.31,<3`.

- [ ] **Step 2: Write race tests with synchronization barriers**

Use `TransactionTestCase`/pytest transaction mode and `threading.Barrier` so two workers attempt the same charge, payment idempotency key, emission or integration key simultaneously.

Expected assertions:

```text
one charge per subscription/cycle
one payment per integration/external_id
one active emission per charge
one completed idempotency record per integration/key
```

- [ ] **Step 3: Run races repeatedly on PostgreSQL**

Run: `SECRET_KEY=test-only-key DATABASE_URL="$SCL_TEST_DATABASE_URL" python manage.py shell -c 'from django.db import connection; assert connection.vendor == "postgresql"'`

Run: `SECRET_KEY=test-only-key DATABASE_URL="$SCL_TEST_DATABASE_URL" python -m pytest tests/concurrency -v --count=10`

Add `pytest-repeat>=0.9,<1` for `--count`.

Expected: PASS in all repetitions; SQLite is not accepted for this gate.

- [ ] **Step 4: Implement Locust license scenario**

Mix 80% active, 10% grace, 10% denied documents. Run 100 concurrent users, spawn rate 10/s for five minutes. Require p95 below 300 ms, error rate below 0.1% and zero incorrect business codes.

- [ ] **Step 5: Implement Locust integration scenario**

Mix incremental GET, single upsert and batch upsert with unique idempotency keys. Run 25 concurrent users, spawn rate 5/s for five minutes. Require no duplicate references, error rate below 0.1% and p95 below 500 ms.

- [ ] **Step 6: Execute and record baseline**

Run:

```bash
locust -f tests/load/license_api.py --headless -u 100 -r 10 -t 5m --host "$SCL_STAGING_URL" --csv /tmp/opencode/scl-license
locust -f tests/load/integration_api.py --headless -u 25 -r 5 -t 5m --host "$SCL_STAGING_URL" --csv /tmp/opencode/scl-integration
python tests/load/assert_results.py /tmp/opencode/scl-license_stats.csv --p95-ms 300 --max-error-rate 0.001 --business-errors /tmp/opencode/scl-license-business-errors.json
python tests/load/assert_results.py /tmp/opencode/scl-integration_stats.csv --p95-ms 500 --max-error-rate 0.001 --business-errors /tmp/opencode/scl-integration-business-errors.json
```

Each Locust scenario writes a machine-readable business-error list and records duplicate-reference checks. `assert_results.py` exits non-zero when p95/error-rate limits fail or any business error/duplicate exists. Write commands, exit codes, results, database size and hardware profile to `_reversa_sdd/analysis-scl/progress.md`. Do not claim performance without recorded output.

- [ ] **Step 7: Suggested commit**

```bash
git add requirements.txt tests/concurrency tests/load
git commit -m "test: add concurrency and load gates"
```

### Task 5: Backup, Migration, and Gradual Rollout

**Files:**
- Create: `_reversa_sdd/runbooks/backup-restore.md`
- Create: `_reversa_sdd/runbooks/deploy.md`
- Create: `_reversa_sdd/runbooks/rollback.md`
- Create: `_reversa_sdd/runbooks/portal-rollout.md`
- Modify: `_reversa_sdd/analysis-scl/progress.md`

**Interfaces:**
- Produces: executable operator runbooks with commands and expected evidence.

- [ ] **Step 1: Write backup/restore runbook**

Include PostgreSQL `pg_dump --format=custom`, checksum, encrypted storage, `pg_restore --clean --if-exists` into a separate validation database, row-count comparison and application smoke tests.

- [ ] **Step 2: Write deployment runbook**

Order: backup, maintenance notice, image build, explicit migration job, `collectstatic`, web rollout, health check, smoke tests, scheduler activation. Web startup never runs migrations.

Define the billing scheduler exactly once per environment: daily at 00:15 `America/Sao_Paulo`, run `gerar_cobrancas` behind a non-blocking distributed/advisory lock, capture deterministic counters and alert when the command exits non-zero or no success is observed for 26 hours. Schedule `reconciliar_emissoes` every 15 minutes with its own lock after provider adapters are enabled. Record scheduler owner, command, timezone, lock key, last-success evidence and alert destination; overlapping execution must fail closed rather than run twice.

- [ ] **Step 3: Write rollback runbook**

Classify migrations as reversible or restore-required. Include image rollback, feature/access rollback, token key rollback preserving old public keys, gateway webhook pause and database restore decision gate.

- [ ] **Step 4: Define portal rollout cohorts**

```text
cohort 1: superusers and Administrador
cohort 2: Cadastro
cohort 3: Financeiro
cohort 4: Consulta
```

For each cohort require role tests, operational checklist, seven-day error observation and explicit approval before the next cohort. Admin remains contingency throughout.

- [ ] **Step 5: Execute final verification matrix**

Run all pytest suites on PostgreSQL, `manage.py check --deploy`, license consumer smoke test, integration OAuth/upsert/payment smoke test, and sandbox smoke tests for Efí, Sicredi and Sicoob across every method enabled on each contracted account. Gate H is mandatory: release fails if any provider spec, provider implementation plan, adapter implementation, contract suite, sandbox evidence or production-homologation approval is missing.

Start the release candidate with `SCL_ENV_FILE=.env docker compose up -d --wait`; require both `db` and `web` healthy in `docker compose ps`, then call `/health/` from outside the container and record status/body. Any unhealthy service blocks release.

- [ ] **Step 6: Record release evidence**

Store command, timestamp, environment, pass/fail counts, performance percentiles, backup checksum and approver in `_reversa_sdd/analysis-scl/progress.md`.

- [ ] **Step 7: Suggested commit**

```bash
git add _reversa_sdd/runbooks _reversa_sdd/analysis-scl/progress.md
git commit -m "docs: add scl production rollout runbooks"
```
