# SCL Manual Finance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar configuração financeira, geração idempotente de cobranças, pagamentos manuais, estornos e cadastro seguro das contas de gateway.

**Architecture:** Criar o app `financeiro`. Regras ficam em services transacionais; consultas de saldo e inadimplência ficam em selectors puros. O gerador é um management command idempotente, sem Celery.

**Tech Stack:** Django ORM, PostgreSQL, python-dateutil, cryptography/Fernet, Django Templates, pytest-django.

**Spec:** `_reversa_sdd/specs/2026-09-20-scl-licenciamento-financeiro-design.md`

## Global Constraints

- Dia de vencimento entre 1 e 28 e carência maior ou igual a zero.
- Cobrança guarda `fim_carencia` como fotografia da política usada na emissão.
- Status vencido é calculado; não é persistido como fonte de verdade.
- Restrição única por assinatura e competência.
- Pagamento acima do saldo é rejeitado; pagamento parcial mantém saldo aberto.
- Só Administrador e Financeiro registram/estornam pagamentos.
- Segredos de gateway são criptografados com chave externa ao banco.
- Commits somente com autorização.

---

### Task 1: Financial Models and Constraints

**Files:**
- Create: `financeiro/__init__.py`
- Create: `financeiro/apps.py`
- Create: `financeiro/models.py`
- Create: `financeiro/admin.py`
- Create: `financeiro/migrations/__init__.py`
- Create: `financeiro/tests/__init__.py`
- Create: `financeiro/tests/conftest.py`
- Create: `financeiro/tests/test_models.py`
- Modify: `app/settings.py`
- Modify: `app/admin.py`

**Interfaces:**
- Produces: `ConfiguracaoFinanceira`, `Cobranca`, `Pagamento`.
- Produces: enums `Cobranca.Status`, `Pagamento.Origem`, `Pagamento.Status`.

- [ ] **Step 1: Write failing model constraint tests**

Create reusable fixtures:

```python
from datetime import date
from itertools import count
import uuid

import pytest

from licencas.models import Cliente, ClienteSistema, Sistema


@pytest.fixture
def assinatura_factory(db):
    documents = count(100000001)

    def next_valid_cpf():
        digits = [int(value) for value in f"{next(documents):09d}"]
        for factor in (10, 11):
            total = sum(digit * weight for digit, weight in zip(digits, range(factor, 1, -1)))
            remainder = (total * 10) % 11
            digits.append(0 if remainder == 10 else remainder)
        return "".join(str(value) for value in digits)

    def factory(**overrides):
        cliente = Cliente.objects.create(
            nome="Empresa Exemplo",
            cnpjcpf=next_valid_cpf(),
            email="financeiro@example.com",
            telefone="11999999999",
            cep="01001000",
            endereco="Praça da Sé",
            endnumero="1",
            endbairro="Sé",
            endcomplemento="Sala 1",
            endUF="SP",
            endcidade="São Paulo",
            endcodpais=55,
            endpais="Brasil",
        )
        sistema = Sistema.objects.create(nome="ERP", codigo=f"erp-{uuid.uuid4().hex[:8]}")
        values = {
            "cliente": cliente,
            "sistema": sistema,
            "valor_recorrente": "199.90",
            "periodicidade": "monthly",
            "data_inicio": date(2026, 1, 1),
            "primeiro_vencimento": date(2026, 1, 5),
        }
        values.update(overrides)
        return ClienteSistema.objects.create(**values)
    return factory


@pytest.fixture
def assinatura(assinatura_factory):
    return assinatura_factory()


@pytest.fixture
def cobranca_payload():
    return {
        "competencia": date(2026, 1, 1),
        "vencimento": date(2026, 1, 5),
        "fim_carencia": date(2026, 1, 10),
        "valor_original": "199.90",
    }
```

Then add the model tests:

```python
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from financeiro.models import Cobranca, ConfiguracaoFinanceira


@pytest.mark.django_db
def test_financial_config_rejects_due_day_29():
    config = ConfiguracaoFinanceira(dia_vencimento=29, dias_carencia=5)
    with pytest.raises(ValidationError):
        config.full_clean()


@pytest.mark.django_db
def test_charge_cycle_is_unique(assinatura, cobranca_payload):
    Cobranca.objects.create(assinatura=assinatura, **cobranca_payload)
    with pytest.raises(IntegrityError):
        Cobranca.objects.create(assinatura=assinatura, **cobranca_payload)
```

- [ ] **Step 2: Verify model tests fail**

Run: `SECRET_KEY=test-only-key python -m pytest financeiro/tests/test_models.py -v`

Expected: app/model import failure.

- [ ] **Step 3: Implement ConfiguracaoFinanceira**

Use a singleton row with primary key fixed to 1 by model, service/form validation and a database check:

```python
class ConfiguracaoFinanceira(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    dia_vencimento = models.PositiveSmallIntegerField(default=5)
    dias_carencia = models.PositiveSmallIntegerField(default=0)
    timezone = models.CharField(max_length=64, default="America/Sao_Paulo")
    alterado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    alterado_em = models.DateTimeField(auto_now=True)
```

Add `CheckConstraint` for day 1-28 and `CheckConstraint(condition=Q(pk=1), name="finance_config_singleton_pk")`. Override `save()` to force `pk=1`, and test that direct ORM insertion of a second row is rejected by the database.

- [ ] **Step 4: Implement Cobranca**

Required fields:

```python
assinatura = models.ForeignKey("licencas.ClienteSistema", on_delete=models.PROTECT, related_name="cobrancas")
competencia = models.DateField()
vencimento = models.DateField()
fim_carencia = models.DateField()
valor_original = models.DecimalField(max_digits=12, decimal_places=2)
status = models.CharField(max_length=16, choices=Status.choices, default=Status.ABERTA)
descricao = models.CharField(max_length=255, blank=True)
origem = models.CharField(max_length=16, default="scl")
cancelada_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="cobrancas_canceladas")
cancelada_em = models.DateTimeField(null=True, blank=True)
motivo_cancelamento = models.TextField(blank=True)
criado_em = models.DateTimeField(auto_now_add=True)
alterado_em = models.DateTimeField(auto_now=True)
```

Constrain positive amount, grace end on/after due date, and unique `(assinatura, competencia)`. Tests prove `alterado_em` advances on an audited mutation because integration ETags and `updated_since` depend on it.

- [ ] **Step 5: Implement Pagamento**

Use origins `manual`, `gateway`, `legacy`; statuses `confirmed`, `reversed`. Store value, paid timestamp, method, external identifier, manual user, confirmation actor/time, reversal actor/time/reason and audit timestamps. Constrain positive amount. Task 4 adds nullable gateway-emission/provider provenance; Plan 05 adds nullable integration provenance after the integration app exists. External IDs must be unique within their provider/integration scope, not globally.

- [ ] **Step 6: Migrate and run tests**

Run: `SECRET_KEY=test-only-key DATABASE_URL="$SCL_TEST_DATABASE_URL" python manage.py makemigrations financeiro`

Run: `SECRET_KEY=test-only-key DATABASE_URL="$SCL_TEST_DATABASE_URL" python manage.py migrate`

Run: `SECRET_KEY=test-only-key python -m pytest financeiro/tests/test_models.py -v`

Expected: PASS.

- [ ] **Step 7: Suggested commit**

```bash
git add financeiro app/settings.py app/admin.py
git commit -m "feat: add financial ledger models"
```

### Task 2: Billing Schedule and Idempotent Generator

**Files:**
- Create: `financeiro/services/__init__.py`
- Create: `financeiro/services/cobrancas.py`
- Create: `financeiro/management/__init__.py`
- Create: `financeiro/management/commands/__init__.py`
- Create: `financeiro/management/commands/gerar_cobrancas.py`
- Create: `financeiro/tests/test_cobranca_service.py`
- Create: `financeiro/tests/test_gerar_cobrancas_command.py`

**Interfaces:**
- Produces: `meses_por_periodicidade(periodicidade: str) -> int`.
- Produces: `gerar_cobrancas_assinatura(assinatura, *, ate: date | None = None) -> list[Cobranca]`.
- Produces: command `python manage.py gerar_cobrancas --today YYYY-MM-DD`.

- [ ] **Step 1: Write failing recurrence boundary tests**

```python
from datetime import date

import pytest

from financeiro.services.cobrancas import gerar_cobrancas_assinatura


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("periodicidade", "expected"),
    [
        ("monthly", [date(2026, 1, 5), date(2026, 2, 5), date(2026, 3, 5)]),
        ("quarterly", [date(2026, 1, 5), date(2026, 4, 5)]),
        ("semiannual", [date(2026, 1, 5), date(2026, 7, 5)]),
        ("annual", [date(2026, 1, 5), date(2027, 1, 5)]),
    ],
)
def test_generates_expected_calendar_cycles(assinatura_factory, periodicidade, expected):
    assinatura = assinatura_factory(periodicidade=periodicidade, primeiro_vencimento=date(2026, 1, 5))
    charges = gerar_cobrancas_assinatura(assinatura, ate=expected[-1])
    assert [charge.vencimento for charge in charges] == expected
```

Also test fixed term, indefinite one-upcoming-charge behavior, grace snapshot, inactive subscription, and two repeated calls producing no duplicates.

- [ ] **Step 2: Verify service tests fail**

Run: `SECRET_KEY=test-only-key python -m pytest financeiro/tests/test_cobranca_service.py -v`

Expected: missing service.

- [ ] **Step 3: Implement recurrence with relativedelta**

```python
MONTHS = {"monthly": 1, "quarterly": 3, "semiannual": 6, "annual": 12}


def meses_por_periodicidade(periodicidade):
    return MONTHS[periodicidade]
```

Resolve effective grace from subscription override or singleton config. Use `get_or_create` inside `transaction.atomic()` and catch `IntegrityError` caused by concurrent insertion by fetching the existing row.

- [ ] **Step 4: Implement command result reporting**

Output deterministic counters:

```text
subscriptions_scanned=<n>
charges_created=<n>
charges_existing=<n>
subscriptions_failed=<n>
```

`--today` is required by tests and optional in production. One failed subscription is logged and counted without aborting all others; command exits non-zero when failures exist.

- [ ] **Step 5: Run service and command tests**

Run: `SECRET_KEY=test-only-key python -m pytest financeiro/tests/test_cobranca_service.py financeiro/tests/test_gerar_cobrancas_command.py -v`

Expected: PASS.

- [ ] **Step 6: Suggested commit**

```bash
git add financeiro/services financeiro/management financeiro/tests
git commit -m "feat: generate recurring charges idempotently"
```

### Task 3: Financial Position, Payments, and Reversals

**Files:**
- Create: `financeiro/selectors.py`
- Create: `financeiro/services/pagamentos.py`
- Create: `financeiro/tests/test_financial_position.py`
- Create: `financeiro/tests/test_pagamento_service.py`

**Interfaces:**
- Produces: immutable `FinancialPosition(code, allowed, oldest_due_date, grace_ends_on, outstanding_amount)`.
- Produces: `obter_posicao_financeira(assinatura, *, hoje: date) -> FinancialPosition`.
- Produces: `registrar_pagamento_manual(...) -> Pagamento` and `estornar_pagamento(...) -> Pagamento`.
- Produces: `cancelar_cobranca_scl(cobranca, *, motivo, usuario) -> Cobranca`.

- [ ] **Step 1: Write the exact date-boundary tests**

Cover:

```python
assert obter_posicao_financeira(assinatura, hoje=date(2026, 1, 5)).code == "CURRENT"
assert obter_posicao_financeira(assinatura, hoje=date(2026, 1, 6)).code == "OVERDUE_IN_GRACE"
assert obter_posicao_financeira(assinatura, hoje=date(2026, 1, 10)).code == "OVERDUE_IN_GRACE"
assert obter_posicao_financeira(assinatura, hoje=date(2026, 1, 11)).code == "DELINQUENT"
```

Also test grace zero, oldest of multiple balances, partial payment, full payment, reversed payment and canceled charges. A canceled charge never contributes to balance, grace, delinquency or license denial. Cancellation is rejected for non-SCL origin, confirmed payments or active external emission.

- [ ] **Step 2: Verify tests fail**

Run: `SECRET_KEY=test-only-key python -m pytest financeiro/tests/test_financial_position.py financeiro/tests/test_pagamento_service.py -v`

Expected: missing selector/services.

- [ ] **Step 3: Implement balance annotations and position**

Sum only payments whose current status is `confirmed`; a payment changed to `reversed` contributes zero and is not subtracted again. Do not persist an overdue status. The selector orders outstanding charges by `vencimento`, then `pk`. A regression test records a full payment, reverses it and proves the balance returns exactly to its pre-payment value.

- [ ] **Step 4: Implement payment services under row lock**

```python
@transaction.atomic
def registrar_pagamento_manual(*, cobranca, valor, pago_em, forma, usuario):
    locked = Cobranca.objects.select_for_update().get(pk=cobranca.pk)
    saldo = saldo_cobranca(locked)
    if valor <= 0 or valor > saldo:
        raise ValidationError("O valor deve ser positivo e não pode exceder o saldo.")
    pagamento = Pagamento.objects.create(...)
    atualizar_status_cobranca(locked)
    return pagamento
```

Estorno locks payment and charge, rejects duplicate reversal, requires reason, records reversal actor/time, recalculates charge status and appends an `EventoAuditoria` in the same transaction. Payment confirmation does the same; audit failure rolls back the mutation.

`cancelar_cobranca_scl` is a separate atomic service: lock the charge, require `origem="scl"`, no confirmed payment and no active emission, require reason, set canceled status/actor/time, advance `alterado_em`, and append `EventoAuditoria` in the same transaction.

- [ ] **Step 5: Run payment tests**

Run: `SECRET_KEY=test-only-key python -m pytest financeiro/tests/test_financial_position.py financeiro/tests/test_pagamento_service.py -v`

Expected: PASS.

- [ ] **Step 6: Suggested commit**

```bash
git add financeiro/selectors.py financeiro/services/pagamentos.py financeiro/tests
git commit -m "feat: calculate balances and manage payments"
```

### Task 4: Secure Gateway Account and Emission Records

**Files:**
- Modify: `requirements.txt`
- Create: `financeiro/crypto.py`
- Modify: `financeiro/models.py`
- Create: `financeiro/services/contas_gateway.py`
- Create: `financeiro/tests/test_gateway_models.py`
- Create: `financeiro/tests/test_gateway_accounts.py`
- Modify: `app/settings.py`
- Create: migrations in `financeiro/migrations/`
- Modify: `.env.example`

**Interfaces:**
- Produces: `ContaGateway`, `EmissaoCobranca`, `EventoGateway`.
- Produces: `encrypt_config(dict) -> str`, `decrypt_config(str) -> dict`.
- Produces: `salvar_credenciais(conta, *, configuracao, usuario)`.

- [ ] **Step 1: Add cryptography dependency and environment key**

Add `cryptography>=45,<47` and `SCL_CONFIG_ENCRYPTION_KEYS` to `.env.example`. Value is a comma-separated list of Fernet keys, newest first.

- [ ] **Step 2: Write failing encryption and emission constraints tests**

```python
def test_encrypted_configuration_does_not_contain_secret(settings):
    settings.SCL_CONFIG_ENCRYPTION_KEYS = [Fernet.generate_key().decode()]
    ciphertext = encrypt_config({"client_secret": "super-secret"})
    assert "super-secret" not in ciphertext
    assert decrypt_config(ciphertext)["client_secret"] == "super-secret"
```

Also assert multiple accounts for one provider are allowed and only one active emission per charge is allowed.

- [ ] **Step 3: Implement MultiFernet helper**

```python
def _fernet():
    keys = settings.SCL_CONFIG_ENCRYPTION_KEYS
    if not keys:
        raise ImproperlyConfigured("SCL_CONFIG_ENCRYPTION_KEYS is required")
    return MultiFernet([Fernet(key.encode()) for key in keys])
```

Serialize canonical JSON before encryption; decode only inside gateway services.

- [ ] **Step 4: Implement gateway models**

`ContaGateway` fields: public UUID, name, provider (`efi`, `sicredi`, `sicoob`), environment, active, boleto/pix booleans, public configuration JSON, encrypted configuration text, last connection status and audit users.

`EmissaoCobranca` fields: charge, account, method, idempotency key, external ID, status, timestamps, external due date, boleto/PIX presentation fields, normalized error.

`EventoGateway` fields: account, provider snapshot, external event ID, type, payload hash/protected payload, status, attempts and errors. Unique `(provider, external_event_id)` prevents the same provider event entering through two accounts.

Add nullable `Pagamento.emissao_gateway` (`PROTECT`) and `Pagamento.provedor_gateway` snapshot. Gateway payments require both, and `(provedor_gateway, identificador_externo)` is unique for gateway-origin rows. Plan 05 adds the equivalent integration relation/constraint.

Use a partial unique constraint for one emission in active states per charge.

`salvar_credenciais` and account activation/deactivation append sanitized `EventoAuditoria` rows in the same transaction. Tests assert ciphertext and credential values never enter the audit JSON.

- [ ] **Step 5: Run model and encryption tests**

Run: `SECRET_KEY=test-only-key SCL_CONFIG_ENCRYPTION_KEYS=MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA= python -m pytest financeiro/tests/test_gateway_models.py -v`

Expected: PASS with a valid generated Fernet key supplied by the test fixture.

- [ ] **Step 6: Suggested commit**

```bash
git add requirements.txt .env.example app/settings.py financeiro
git commit -m "feat: store gateway accounts and emissions securely"
```

### Task 5: Financial Portal

**Files:**
- Create: `financeiro/forms.py`
- Create: `financeiro/views.py`
- Create: `financeiro/urls.py`
- Create: `financeiro/services/configuracao.py`
- Create: `financeiro/templates/financeiro/cobrancas/list.html`
- Create: `financeiro/templates/financeiro/cobrancas/detail.html`
- Create: `financeiro/templates/financeiro/cobrancas/cancel.html`
- Create: `financeiro/templates/financeiro/pagamentos/list.html`
- Create: `financeiro/templates/financeiro/pagamentos/form.html`
- Create: `financeiro/templates/financeiro/pagamentos/reverse.html`
- Create: `financeiro/templates/financeiro/configuracao/form.html`
- Create: `financeiro/templates/financeiro/gateways/list.html`
- Create: `financeiro/templates/financeiro/gateways/form.html`
- Create: `financeiro/tests/test_views.py`
- Modify: `licencas/forms/assinaturas.py`
- Modify: `licencas/tests/test_assinatura_views.py`
- Modify: `app/urls.py`
- Modify: `templates/partials/_sidebar.html`
- Modify: `portal/management/commands/sync_roles.py`

**Interfaces:**
- Produces: namespaced finance URLs for lists, detail, manual payment, reversal, configuration and gateway accounts.
- Consumes: selectors/services from Tasks 2-4.
- Produces: `alterar_configuracao_financeira(*, values, usuario, motivo) -> ConfiguracaoFinanceira` with durable audit.

- [ ] **Step 1: Write permission and workflow tests**

Test Financeiro/Admin mutation, Cadastro/Consulta read-only behavior, CSRF-enforced rejection for every payment/reversal/charge-cancellation/configuration/credential POST, GET rejection on payment/reversal/cancellation, audited SCL-owned charge cancellation, canceled debt disappearing immediately from license-facing financial position, filters by status/date/client/system, payment-list pagination, partial payment rendering, secret not redisplayed, configuration day/grace validation, and new subscriptions inheriting the configured due day/carência when no override is provided.

- [ ] **Step 2: Verify tests fail**

Run: `SECRET_KEY=test-only-key python -m pytest financeiro/tests/test_views.py -v`

Expected: routes not found.

- [ ] **Step 3: Implement forms and views**

Views must call services, never calculate balances or assign statuses directly. Gateway form accepts secret input as write-only and leaves stored secrets untouched when the field is blank during update.

Configuration changes call `alterar_configuracao_financeira` under row lock and append before/after `EventoAuditoria` data in the same transaction. Tests prove direct crafted POSTs cannot bypass validation/audit.

Replace the temporary day-5 suggestion in `AssinaturaForm` with `ConfiguracaoFinanceira` defaults. Persist `primeiro_vencimento`; keep `dia_vencimento` and `dias_carencia` null when the subscription intentionally inherits global values.

- [ ] **Step 4: Build Duralux financial templates**

Lists include overdue/grace badges, date filters, balance, source and pagination. Detail shows immutable ledger rows. Destructive actions require a separate confirmation page and POST.

- [ ] **Step 5: Run the complete financial gate**

Run: `SECRET_KEY=test-only-key python -m pytest financeiro portal/tests/test_roles.py -v`

Expected: PASS.

Run: `SECRET_KEY=test-only-key DATABASE_URL="$SCL_TEST_DATABASE_URL" python manage.py shell -c 'from django.db import connection; assert connection.vendor == "postgresql"'`

Run: `SECRET_KEY=test-only-key DATABASE_URL="$SCL_TEST_DATABASE_URL" python manage.py gerar_cobrancas --today 2026-09-20`

Expected: deterministic counters and exit 0.

- [ ] **Step 6: Suggested commit**

```bash
git add financeiro licencas/forms/assinaturas.py licencas/tests/test_assinatura_views.py app/urls.py templates/partials/_sidebar.html portal/management/commands/sync_roles.py
git commit -m "feat: add manual financial operations portal"
```
