# SCL Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tornar a base Django segura, testável e consistente com PostgreSQL antes de adicionar funcionalidades.

**Architecture:** Manter `app.settings` único por enquanto, carregando configuração do ambiente com `django-environ`. Remover infraestrutura Celery sem uso, corrigir o container e criar um baseline de testes sobre o legado existente.

**Tech Stack:** Python 3.11+, Django 5.2 LTS, PostgreSQL 16, pytest, pytest-django, django-environ, Docker Compose.

**Spec:** `_reversa_sdd/specs/2026-09-20-scl-licenciamento-financeiro-design.md`

## Global Constraints

- Exige liberação prévia dos caminhos no `.reversa/reversa-config.json` pelo usuário.
- Não presumir que outros ambientes estão vazios, embora o SQLite local tenha contagem zero nas quatro tabelas do domínio.
- Produção usa PostgreSQL; segredos e credenciais não ficam no código.
- Não introduzir Celery ou RabbitMQ.
- Não remover `AcessoMaquina` até seu uso ser decidido.
- Commits só podem ser executados se o usuário inicializar Git e autorizar.

---

### Task 0: Authoritative Database, Backup, and Legacy Disposition Gate

**Files:**
- Create: `_reversa_sdd/runbooks/pre-migration-gate.md`
- Modify: `_reversa_sdd/analysis-scl/progress.md`

**Interfaces:**
- Produces: recorded authoritative-database decision and immutable pre-migration evidence.
- Produces: `SCL_TEST_DATABASE_URL` for disposable PostgreSQL test execution; never infer a migration target from current Django settings or the later SQLite fallback.

- [ ] **Step 1: Identify the authoritative database**

Record environment, owner, database host/name, engine and whether it is disposable, persistent or production. The operator must explicitly confirm the authoritative source before proceeding. The local zero-row SQLite file is evidence only for that file, not for any shared environment.

- [ ] **Step 2: Assert the selected migration target**

Use the PostgreSQL client independently of the current hardcoded Django settings:

```bash
psql "$SCL_TARGET_DATABASE_URL" -v ON_ERROR_STOP=1 -Atc "SELECT current_database(), current_setting('server_version')"
```

Expected: the operator-approved PostgreSQL database name and server version. Never run a schema/data migration when `SCL_TARGET_DATABASE_URL` is unset or this assertion fails. Do not use `manage.py` for this pre-configuration check.

- [ ] **Step 3: Inventory legacy data and decide `AcessoMaquina`**

Record row counts for all domain tables, sample only non-sensitive keys needed for mapping, and usages of the integer fields `AcessoMaquina.cliente`/`sistema`. Choose and record one disposition: preserve as historical, map to foreign keys in a later approved migration, or quarantine. This plan never deletes the table.

- [ ] **Step 4: Back up and restore-test every persistent target**

For any non-disposable target, run PostgreSQL `pg_dump --format=custom`, hash the artifact, store it encrypted, restore it into a separate validation database with `pg_restore --clean --if-exists`, compare table row counts and run read-only application smoke tests. Record commands, timestamps, database identifiers, checksum and operator approval in `progress.md` without recording credentials.

- [ ] **Step 5: Close Gate 0**

Gate 0 passes only when the authoritative database, PostgreSQL assertion, `AcessoMaquina` disposition and restore evidence are recorded. All later `migrate` commands consume an explicit `SCL_TEST_DATABASE_URL` for disposable tests or the separately approved deployment URL.

### Task 1: Test Harness and Environment Settings

**Files:**
- Modify: `requirements.txt`
- Create: `pytest.ini`
- Create: `tests/__init__.py`
- Create: `tests/test_settings.py`
- Modify: `app/settings.py:13-135`
- Create: `.env.example`

**Interfaces:**
- Produces: ambiente configurado por `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DATABASE_URL`, `TIME_ZONE`.
- Produces: comando padrão `python -m pytest`.

- [ ] **Step 1: Replace transitive pins with direct application dependencies**

Use este conjunto inicial:

```text
Django>=5.2,<5.3
django-environ>=0.12,<0.13
django-jazzmin>=3.0,<4
psycopg[binary]>=3.2,<4
pytest>=8,<9
pytest-django>=4.11,<5
python-dateutil>=2.9,<3
```

- [ ] **Step 2: Configure pytest**

```ini
[pytest]
DJANGO_SETTINGS_MODULE = app.settings
python_files = test_*.py
addopts = -ra
```

- [ ] **Step 3: Write failing environment tests**

```python
import importlib

from django.conf import settings


def test_timezone_defaults_to_sao_paulo():
    assert settings.TIME_ZONE == "America/Sao_Paulo"


def test_secret_key_is_not_the_scaffold_value():
    assert "django-insecure-w98yc" not in settings.SECRET_KEY


def test_database_configuration_has_no_literal_password():
    source = importlib.import_module("app.settings").__file__
    assert "Lss167349" not in open(source, encoding="utf-8").read()
```

- [ ] **Step 4: Run tests and verify the secret test fails**

Run: `python -m pytest tests/test_settings.py -v`

Expected: FAIL because `app/settings.py` still contains the scaffold key and database password.

- [ ] **Step 5: Read settings from the environment**

Implement the core shape:

```python
import environ

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env(
    DEBUG=(bool, False),
    TIME_ZONE=(str, "America/Sao_Paulo"),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}
TIME_ZONE = env("TIME_ZONE")
```

Remove the literal PostgreSQL credentials and unused `CELERY_BROKER_URL`.

- [ ] **Step 6: Add a safe environment example**

```dotenv
SECRET_KEY=replace-with-a-long-random-value
DEBUG=true
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgresql://scl:scl@db:5432/scl
TIME_ZONE=America/Sao_Paulo
```

- [ ] **Step 7: Run focused tests**

Run: `SECRET_KEY=test-only-key DEBUG=true python -m pytest tests/test_settings.py -v`

Expected: 3 passed.

- [ ] **Step 8: Suggested commit**

```bash
git add requirements.txt pytest.ini tests app/settings.py .env.example
git commit -m "chore: secure project settings and add test harness"
```

### Task 2: PostgreSQL and Container Baseline

**Files:**
- Create: `Dockerfile`
- Delete: `Dockefile`
- Modify: `docker-compose.yml`
- Create: `.dockerignore`
- Create: `tests/test_container_config.py`

**Interfaces:**
- Consumes: environment variables from Task 1.
- Produces: `db` and `web` services; PostgreSQL health check; no RabbitMQ/Celery services.

- [ ] **Step 1: Write failing container configuration tests**

```python
from pathlib import Path

import yaml


def test_compose_has_only_required_services():
    compose = yaml.safe_load(Path("docker-compose.yml").read_text())
    assert set(compose["services"]) == {"db", "web"}


def test_standard_dockerfile_exists():
    assert Path("Dockerfile").is_file()
    assert not Path("Dockefile").exists()
```

Add `PyYAML>=6,<7` to test dependencies.

- [ ] **Step 2: Run tests and verify failure**

Run: `SECRET_KEY=test-only-key python -m pytest tests/test_container_config.py -v`

Expected: FAIL because Celery/RabbitMQ exist and `Dockerfile` does not.

- [ ] **Step 3: Create the production-shaped Dockerfile**

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

- [ ] **Step 4: Replace Compose with PostgreSQL 16 and web**

Use `postgres:16-alpine`, named volume `postgres_data`, `pg_isready` health check, `env_file: ${SCL_ENV_FILE:-.env}`, and `depends_on.db.condition: service_healthy`. Add a `web` healthcheck that calls `/health/` with Python `urllib` (available in the image), sending `X-Forwarded-Proto: https` so production `SECURE_SSL_REDIRECT` does not redirect the internal plain-HTTP probe; use interval 30s, timeout 5s and three retries. Do not run migrations automatically in the web command. The operator creates the real `.env`; automation must not synthesize production secrets.

- [ ] **Step 5: Add `.dockerignore`**

```text
.git
.env
venv/
__pycache__/
*.py[cod]
db.sqlite3
data/
staticfiles/
_reversa_docs/
```

- [ ] **Step 6: Verify configuration**

Run: `SCL_ENV_FILE=.env.example docker compose config`

Expected: exit 0; only `db` and `web` services.

Run: `SECRET_KEY=test-only-key python -m pytest tests/test_container_config.py -v`

Expected: 2 passed.

- [ ] **Step 7: Suggested commit**

```bash
git add Dockerfile docker-compose.yml .dockerignore requirements.txt tests/test_container_config.py
git rm Dockefile
git commit -m "chore: align containers with postgres runtime"
```

### Task 3: Characterize and Repair Existing Models

**Files:**
- Delete: `licencas/tests.py`
- Create: `licencas/tests/__init__.py`
- Create: `licencas/tests/test_legacy_models.py`
- Modify: `licencas/models.py:47-82`
- Create: migration generated by `makemigrations licencas`

**Interfaces:**
- Produces: valid string representations for `ClienteSistema` and `AcessoMaquina`.
- Preserves: current tables and `PROTECT` behavior.

- [ ] **Step 1: Write failing representation tests**

```python
import pytest

from licencas.models import AcessoMaquina, Cliente, ClienteSistema, Sistema


@pytest.mark.django_db
def test_cliente_sistema_string_contains_both_names():
    cliente = Cliente.objects.create(nome="Acme", cnpjcpf="123", email="a@b.com", telefone="1", cep="1", endereco="Rua", endnumero="1", endbairro="B", endcomplemento="-", endUF="SP", endcidade="C", endcodpais=55, endpais="Brasil")
    sistema = Sistema.objects.create(nome="ERP")
    vinculo = ClienteSistema.objects.create(cliente=cliente, sistema=sistema)
    assert str(vinculo) == "Acme - ERP"


@pytest.mark.django_db
def test_acesso_string_is_text():
    acesso = AcessoMaquina(cliente=10, sistema=20)
    assert str(acesso) == "Cliente 10 - Sistema 20"
```

- [ ] **Step 2: Verify tests fail**

Run: `SECRET_KEY=test-only-key python -m pytest licencas/tests/test_legacy_models.py -v`

Expected: FAIL with non-string `__str__` behavior.

- [ ] **Step 3: Implement minimal repairs**

```python
def __str__(self):
    return f"{self.cliente} - {self.sistema}"
```

For `AcessoMaquina`:

```python
def __str__(self):
    return f"Cliente {self.cliente} - Sistema {self.sistema}"
```

- [ ] **Step 4: Generate and inspect migrations**

Run: `SECRET_KEY=test-only-key python manage.py makemigrations licencas --check --dry-run`

If Django reports the existing `verbose_name` drift, generate the options migration and verify that it does not drop or recreate tables.

- [ ] **Step 5: Run app tests**

Run: `SECRET_KEY=test-only-key python -m pytest licencas/tests/test_legacy_models.py -v`

Expected: PASS.

- [ ] **Step 6: Suggested commit**

```bash
git add licencas/models.py licencas/tests licencas/migrations
git rm licencas/tests.py
git commit -m "fix: repair legacy model representations"
```

### Task 4: Health Endpoint and Final Foundation Gate

**Files:**
- Create: `app/health.py`
- Modify: `app/urls.py`
- Create: `tests/test_health.py`

**Interfaces:**
- Produces: `GET /health/` returning `{"status": "ok"}` after a database probe.

- [ ] **Step 1: Write the failing health test**

```python
import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_health_endpoint_checks_database(client):
    response = client.get(reverse("health"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Verify it fails**

Run: `SECRET_KEY=test-only-key python -m pytest tests/test_health.py -v`

Expected: FAIL because route `health` does not exist.

- [ ] **Step 3: Implement the endpoint**

```python
from django.db import connection
from django.http import JsonResponse


def health(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return JsonResponse({"status": "ok"})
```

Map it with `path("health/", health, name="health")`.

- [ ] **Step 4: Run the complete foundation gate**

Run: `SECRET_KEY=test-only-key DEBUG=true python manage.py check`

Expected: no issues.

Run: `SECRET_KEY=test-only-key DEBUG=true python -m pytest -v`

Expected: all foundation and characterization tests pass.

Run: `SECRET_KEY=test-only-key DEBUG=false ALLOWED_HOSTS=example.com python manage.py check --deploy`

Expected: only warnings explicitly deferred to the hardening plan; record each warning in `_reversa_sdd/analysis-scl/progress.md`.

- [ ] **Step 5: Suggested commit**

```bash
git add app/health.py app/urls.py tests/test_health.py
git commit -m "feat: add database health endpoint"
```
