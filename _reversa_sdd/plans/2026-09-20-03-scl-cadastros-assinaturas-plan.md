# SCL Cadastros and Subscriptions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar cadastros de clientes, sistemas e assinaturas cliente-sistema com validação, filtros, permissões e histórico preservado.

**Architecture:** Evoluir os modelos existentes no app `licencas`, mantendo as tabelas atuais. Views finas usam `ModelForm`, selectors para consultas e services para transições de assinatura.

**Tech Stack:** Django ORM, Django Forms, python-stdnum, Django Templates, pytest-django.

**Spec:** `_reversa_sdd/specs/2026-09-20-scl-licenciamento-financeiro-design.md`

## Global Constraints

- CNPJ/CPF é normalizado para dígitos, validado e único.
- Cliente inativo ou bloqueado não pode receber autorização de licença.
- O par cliente-sistema é único.
- Dia de vencimento, quando informado, fica entre 1 e 28; carência não pode ser negativa.
- Uma assinatura encerrada pode ser reativada no mesmo vínculo; não criar segundo vínculo para o mesmo par.
- Não remover `AcessoMaquina`.
- Commits somente com autorização.

---

### Task 1: Document Validation and Legacy Data Audit

**Files:**
- Modify: `requirements.txt`
- Create: `licencas/validators.py`
- Create: `licencas/management/__init__.py`
- Create: `licencas/management/commands/__init__.py`
- Create: `licencas/management/commands/audit_legacy_data.py`
- Create: `licencas/tests/test_validators.py`
- Create: `licencas/tests/test_audit_command.py`

**Interfaces:**
- Produces: `normalize_document(value: str) -> str`.
- Produces: `validate_document(value: str) -> None`, raising `ValidationError`.
- Produces: `python manage.py audit_legacy_data`, exit non-zero on invalid or duplicate documents/vínculos.

- [ ] **Step 1: Add document validation dependency**

Add `python-stdnum>=1.20,<2`.

- [ ] **Step 2: Write failing validator tests**

```python
import pytest
from django.core.exceptions import ValidationError

from licencas.validators import normalize_document, validate_document


def test_normalize_document_removes_mask():
    assert normalize_document("12.345.678/0001-95") == "12345678000195"


def test_validate_document_accepts_valid_cnpj():
    validate_document("12.345.678/0001-95")


def test_validate_document_rejects_invalid_value():
    with pytest.raises(ValidationError):
        validate_document("11111111111")
```

- [ ] **Step 3: Verify validator tests fail**

Run: `SECRET_KEY=test-only-key python -m pytest licencas/tests/test_validators.py -v`

Expected: import failure.

- [ ] **Step 4: Implement normalization and validation**

```python
import re
from django.core.exceptions import ValidationError
from stdnum.br import cnpj, cpf


def normalize_document(value):
    return re.sub(r"\D", "", value or "")


def validate_document(value):
    normalized = normalize_document(value)
    valid = cpf.is_valid(normalized) if len(normalized) == 11 else cnpj.is_valid(normalized) if len(normalized) == 14 else False
    if not valid:
        raise ValidationError("Informe um CPF ou CNPJ válido.")
```

- [ ] **Step 5: Implement a read-only audit command**

The command must report:

```text
invalid_documents=<count>
duplicate_documents=<count>
duplicate_client_system_pairs=<count>
```

It must never modify rows. Raise `CommandError` when any count is non-zero.

- [ ] **Step 6: Run focused tests and command**

Run: `SECRET_KEY=test-only-key python -m pytest licencas/tests/test_validators.py licencas/tests/test_audit_command.py -v`

Expected: PASS.

Run: `SECRET_KEY=test-only-key DATABASE_URL="$SCL_TARGET_DATABASE_URL" python manage.py audit_legacy_data`

Expected: counts recorded for the operator-approved target; the gate passes only when all counts are zero or an explicit remediation plan is completed before migrations.

- [ ] **Step 7: Suggested commit**

```bash
git add requirements.txt licencas/validators.py licencas/management licencas/tests
git commit -m "feat: validate documents and audit legacy data"
```

### Task 2: Evolve Cliente and Sistema Safely

**Files:**
- Modify: `licencas/models.py:4-44`
- Create: `licencas/tests/conftest.py`
- Create: `licencas/tests/test_cliente_sistema_models.py`
- Modify: `licencas/tests/test_legacy_models.py`
- Create: migrations generated in `licencas/migrations/`

**Interfaces:**
- Produces: `Cliente.documento_normalizado` behavior through `clean()`/`save()`.
- Produces: `Sistema.codigo` unique immutable business identifier.

- [ ] **Step 1: Write failing model tests**

Define the shared payload first:

```python
import pytest


@pytest.fixture
def cliente_payload():
    return {
        "nome": "Empresa Exemplo",
        "email": "financeiro@example.com",
        "telefone": "11999999999",
        "cep": "01001000",
        "endereco": "Praça da Sé",
        "endnumero": "1",
        "endbairro": "Sé",
        "endcomplemento": "Sala 1",
        "endUF": "SP",
        "endcidade": "São Paulo",
        "endcodpais": 55,
        "endpais": "Brasil",
    }
```

Then add the tests:

```python
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from licencas.models import Cliente, Sistema


@pytest.mark.django_db
def test_cliente_normalizes_document_before_save(cliente_payload):
    cliente = Cliente(**cliente_payload, cnpjcpf="12.345.678/0001-95")
    cliente.full_clean()
    cliente.save()
    assert cliente.cnpjcpf == "12345678000195"


@pytest.mark.django_db
def test_cliente_block_requires_reason(cliente_payload):
    cliente = Cliente(**cliente_payload, cnpjcpf="12345678000195", bloqueado=True)
    with pytest.raises(ValidationError):
        cliente.full_clean()


@pytest.mark.django_db
def test_sistema_code_is_unique():
    Sistema.objects.create(nome="ERP", codigo="erp")
    with pytest.raises(IntegrityError):
        Sistema.objects.create(nome="Outro", codigo="erp")
```

- [ ] **Step 2: Verify tests fail**

Run: `SECRET_KEY=test-only-key python -m pytest licencas/tests/test_cliente_sistema_models.py -v`

Expected: missing fields and normalization behavior.

- [ ] **Step 3: Add Cliente fields and validation**

Add:

```python
cnpjcpf = models.CharField(max_length=14, unique=True, validators=[validate_document])
bloqueado = models.BooleanField(default=False)
motivo_bloqueio = models.TextField(blank=True)
bloqueado_em = models.DateTimeField(null=True, blank=True)
```

Normalize in `clean()` and again in `save()` to protect non-form callers. Require `motivo_bloqueio` when blocked and clear `bloqueado_em` when unblocked through the service layer.

- [ ] **Step 4: Add Sistema fields**

```python
codigo = models.SlugField(max_length=50, unique=True)
descricao = models.TextField(blank=True)
```

Treat `codigo` as immutable after creation in the form and service.

- [ ] **Step 5: Create defensive schema and data migrations**

Migration sequence:

1. Add new fields nullable where necessary.
2. Normalize existing documents and detect collisions; abort with row IDs if collisions exist.
3. Populate system codes from slugified name plus primary key on collision.
4. Apply non-null/unique constraints only after the operator records remediation for every unresolved row.

Do not assume the local zero-row database represents production. Do not run this sequence until Plan 01 Gate 0 is closed.

Update `test_legacy_models.py` in this task so `Cliente` uses a valid document and `Sistema` supplies `codigo`, preserving the representation regression test after the new constraints.

- [ ] **Step 6: Run model and migration tests**

Run: `SECRET_KEY=test-only-key DATABASE_URL="$SCL_TEST_DATABASE_URL" python manage.py migrate`

Run: `SECRET_KEY=test-only-key python -m pytest licencas/tests/test_cliente_sistema_models.py -v`

Expected: PASS.

- [ ] **Step 7: Suggested commit**

```bash
git add licencas/models.py licencas/migrations licencas/tests/conftest.py licencas/tests/test_cliente_sistema_models.py licencas/tests/test_legacy_models.py
git commit -m "feat: strengthen client and system records"
```

### Task 3: Evolve ClienteSistema into a Subscription

**Files:**
- Modify: `licencas/models.py:47-60`
- Create: `licencas/services/__init__.py`
- Create: `licencas/services/assinaturas.py`
- Create: `licencas/management/commands/prepare_subscription_migration.py`
- Modify: `licencas/tests/conftest.py`
- Create: `licencas/tests/test_assinatura_model.py`
- Create: `licencas/tests/test_subscription_migration_command.py`
- Modify: `licencas/tests/test_legacy_models.py`
- Create: migrations in `licencas/migrations/`

**Interfaces:**
- Produces: `ClienteSistema.Periodicidade` choices `MENSAL`, `TRIMESTRAL`, `SEMESTRAL`, `ANUAL`.
- Produces: `ativar_assinatura(assinatura, *, usuario)` and `bloquear_assinatura(assinatura, *, motivo, usuario)`.

- [ ] **Step 1: Write failing subscription invariants**

Add the fixture:

```python
from datetime import date

from licencas.models import Cliente, ClienteSistema, Sistema


@pytest.fixture
def assinatura(db, cliente_payload):
    cliente = Cliente.objects.create(**cliente_payload, cnpjcpf="12345678000195")
    sistema = Sistema.objects.create(nome="ERP", codigo="erp")
    return ClienteSistema.objects.create(
        cliente=cliente,
        sistema=sistema,
        valor_recorrente="199.90",
        periodicidade="monthly",
        data_inicio=date(2026, 1, 1),
        primeiro_vencimento=date(2026, 1, 5),
    )
```

Then add the invariants:

```python
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from licencas.models import ClienteSistema


def test_subscription_rejects_due_day_above_28(assinatura):
    assinatura.dia_vencimento = 29
    with pytest.raises(ValidationError):
        assinatura.full_clean()


def test_subscription_rejects_end_before_start(assinatura):
    assinatura.data_fim = assinatura.data_inicio.replace(year=assinatura.data_inicio.year - 1)
    with pytest.raises(ValidationError):
        assinatura.full_clean()


@pytest.mark.django_db
def test_client_system_pair_is_unique(assinatura):
    with pytest.raises(IntegrityError):
        ClienteSistema.objects.create(cliente=assinatura.cliente, sistema=assinatura.sistema)
```

- [ ] **Step 2: Verify tests fail**

Run: `SECRET_KEY=test-only-key python -m pytest licencas/tests/test_assinatura_model.py -v`

Expected: missing fields/constraints.

- [ ] **Step 3: Add subscription fields**

```python
class Periodicidade(models.TextChoices):
    MENSAL = "monthly", "Mensal"
    TRIMESTRAL = "quarterly", "Trimestral"
    SEMESTRAL = "semiannual", "Semestral"
    ANUAL = "annual", "Anual"

valor_recorrente = models.DecimalField(max_digits=12, decimal_places=2)
periodicidade = models.CharField(max_length=10, choices=Periodicidade.choices)
data_inicio = models.DateField()
data_fim = models.DateField(null=True, blank=True)
primeiro_vencimento = models.DateField()
bloqueado = models.BooleanField(default=False)
motivo_bloqueio = models.TextField(blank=True)
bloqueado_em = models.DateTimeField(null=True, blank=True)
dia_vencimento = models.PositiveSmallIntegerField(null=True, blank=True)
dias_carencia = models.PositiveSmallIntegerField(null=True, blank=True)
```

Add check constraints for day 1-28, non-negative grace, unique `(cliente, sistema)`, and amount rules: active subscriptions require `valor_recorrente > 0`; inactive legacy subscriptions may temporarily keep `valor_recorrente = 0` until corrected.

- [ ] **Step 4: Stage existing links without changing activation**

Split this evolution into a nullable schema migration, an explicit remediation command and a final constraint migration. Preserve every existing row's `ativo` value. The schema migration may derive only:

- `periodicidade=monthly`;
- `data_inicio=criado_em.date()`;
- `primeiro_vencimento` to the next day 5 on or after `data_inicio`.

Leave `valor_recorrente` null for unresolved existing rows. A read-only report must list each row with missing commercial data. Before the final constraint migration, the operator must either supply a positive amount and confirm the row remains active, or explicitly deactivate it with a recorded reason. The command must abort while any row remains unresolved; it must never mass-deactivate customers.

The final constraint allows zero only when `ativo=False`; active rows require a positive amount and all final fields are non-null where defined by the model. Add migration tests proving activation state is preserved, unresolved rows block finalization, activation with zero is rejected and activation succeeds after a positive value is saved.

Implement exact command modes:

```bash
DATABASE_URL="$SCL_TARGET_DATABASE_URL" python manage.py prepare_subscription_migration --report
DATABASE_URL="$SCL_TARGET_DATABASE_URL" python manage.py prepare_subscription_migration --resolve ID --amount 199.90 --periodicity monthly --first-due 2026-10-05 --keep-active --reason "commercial validation"
DATABASE_URL="$SCL_TARGET_DATABASE_URL" python manage.py prepare_subscription_migration --deactivate ID --reason "operator confirmed inactive legacy link"
DATABASE_URL="$SCL_TARGET_DATABASE_URL" python manage.py prepare_subscription_migration --check
```

`--report` is read-only; mutation modes lock one row and append `EventoAuditoria`; `--check` exits non-zero and lists IDs while any required field remains unresolved. The final constraint migration may run only after `--check` exits zero. Update `test_legacy_models.py` with all required subscription fields so the original representation regression remains valid.

- [ ] **Step 5: Implement transition services**

Services use `transaction.atomic()`, `select_for_update()`, set timestamps, call `full_clean()`, save explicit update fields, and write `EventoAuditoria` through `portal.audit.registrar_evento_auditoria` in the same transaction. Cover activation, block/unblock and commercial-field changes; audit failure rolls back the mutation.

- [ ] **Step 6: Run subscription tests**

Run: `SECRET_KEY=test-only-key python -m pytest licencas/tests/test_assinatura_model.py -v`

Expected: PASS.

- [ ] **Step 7: Suggested commit**

```bash
git add licencas/models.py licencas/migrations licencas/services licencas/management/commands/prepare_subscription_migration.py licencas/tests
git commit -m "feat: model client system subscriptions"
```

### Task 4: Cliente and Sistema Portal CRUD

**Files:**
- Create: `licencas/forms/__init__.py`
- Create: `licencas/forms/clientes.py`
- Create: `licencas/forms/sistemas.py`
- Create: `licencas/services/clientes.py`
- Create: `licencas/services/sistemas.py`
- Create: `licencas/selectors.py`
- Create: `licencas/views/__init__.py`
- Create: `licencas/views/clientes.py`
- Create: `licencas/views/sistemas.py`
- Create: `licencas/urls.py`
- Create: `licencas/templates/licencas/clientes/list.html`
- Create: `licencas/templates/licencas/clientes/form.html`
- Create: `licencas/templates/licencas/clientes/detail.html`
- Create: `licencas/templates/licencas/sistemas/list.html`
- Create: `licencas/templates/licencas/sistemas/form.html`
- Create: `licencas/templates/licencas/sistemas/detail.html`
- Create: `licencas/tests/test_cliente_views.py`
- Create: `licencas/tests/test_sistema_views.py`
- Modify: `app/urls.py`
- Modify: `templates/partials/_sidebar.html`

**Interfaces:**
- Produces: namespaced URLs `licencas:cliente-list`, `cliente-create`, `cliente-detail`, `cliente-update`, and system equivalents.
- Produces: GET filters `q`, `status`, `page`.
- Produces: service-backed client/system create/update/block transitions with durable audit.

- [ ] **Step 1: Write permission, filter, validation, and PRG tests**

Test anonymous redirect, Consulta read-only, Cadastro create/update, CSRF-enforced rejection of crafted mutation POSTs, invalid document rendering, `q` matching name/document, status filtering, system/client detail pages, page size 25, and POST redirect after success.

- [ ] **Step 2: Verify tests fail**

Run: `SECRET_KEY=test-only-key python -m pytest licencas/tests/test_cliente_views.py licencas/tests/test_sistema_views.py -v`

Expected: routes not found.

- [ ] **Step 3: Implement selectors**

```python
def listar_clientes(*, q="", status=""):
    queryset = Cliente.objects.all().order_by("nome", "pk")
    if q:
        queryset = queryset.filter(Q(nome__icontains=q) | Q(cnpjcpf__icontains=normalize_document(q)))
    if status == "active":
        queryset = queryset.filter(ativo=True, bloqueado=False)
    elif status == "blocked":
        queryset = queryset.filter(bloqueado=True)
    elif status == "inactive":
        queryset = queryset.filter(ativo=False)
    return queryset
```

Use equivalent explicit filters for systems.

- [ ] **Step 4: Implement ModelForms and views**

Forms normalize documents, make `Sistema.codigo` read-only on update, and render Duralux classes explicitly. Views use `login_required`, `permission_required`, `Paginator(..., 25)`, messages, and Post/Redirect/Get. Client/system views never call `ModelForm.save()` directly: transactional services validate, lock updates and append sanitized `EventoAuditoria` rows for create, update, block/unblock and activation changes.

- [ ] **Step 5: Build accessible templates**

Lists include filter form, result count, responsive table, empty state, status badge, actions, and pagination preserving query parameters. Forms render field and non-field errors and include Cancelar/Salvar actions.

- [ ] **Step 6: Run CRUD tests**

Run: `SECRET_KEY=test-only-key python -m pytest licencas/tests/test_cliente_views.py licencas/tests/test_sistema_views.py -v`

Expected: PASS.

- [ ] **Step 7: Suggested commit**

```bash
git add licencas/forms licencas/services/clientes.py licencas/services/sistemas.py licencas/views licencas/selectors.py licencas/urls.py licencas/templates licencas/tests app/urls.py templates/partials/_sidebar.html
git commit -m "feat: add client and system portal management"
```

### Task 5: Subscription Portal Workflow

**Files:**
- Create: `licencas/forms/assinaturas.py`
- Create: `licencas/views/assinaturas.py`
- Create: `licencas/templates/licencas/assinaturas/list.html`
- Create: `licencas/templates/licencas/assinaturas/form.html`
- Create: `licencas/templates/licencas/assinaturas/detail.html`
- Create: `licencas/templates/licencas/assinaturas/confirm_action.html`
- Create: `licencas/tests/test_assinatura_views.py`
- Modify: `licencas/urls.py`
- Modify: `templates/partials/_sidebar.html`
- Modify: `portal/management/commands/sync_roles.py`

**Interfaces:**
- Produces: URLs `assinatura-list/create/detail/update/block/unblock/activate/deactivate`.
- Consumes: transition services from Task 3.

- [ ] **Step 1: Write workflow tests**

Cover list filters by client/system/status/periodicity, duplicate pair validation, fixed and indefinite terms, Cadastro mutations, Consulta read-only, block reason required, every state mutation rejecting GET, and CSRF-enforced rejection of activate/deactivate/block/unblock POSTs without a valid token.

- [ ] **Step 2: Verify tests fail**

Run: `SECRET_KEY=test-only-key python -m pytest licencas/tests/test_assinatura_views.py -v`

Expected: missing forms/routes.

- [ ] **Step 3: Implement form defaults**

The form suggests `primeiro_vencimento` using day 5 until `ConfiguracaoFinanceira` exists. It must not silently overwrite a user-provided date. Validate end date, amount, day and grace.

- [ ] **Step 4: Implement list/detail and explicit POST actions**

Mutations call services; they do not set model flags directly in views. Use `select_related("cliente", "sistema")` in selectors.

- [ ] **Step 5: Synchronize permissions and sidebar**

Cadastro and Administrador receive add/change/view permissions. Financeiro and Consulta receive view permission. Menu rendering checks `perms.licencas.view_clientesistema`.

- [ ] **Step 6: Run the complete cadastros gate**

Run: `SECRET_KEY=test-only-key python -m pytest licencas portal/tests/test_roles.py -v`

Expected: PASS.

Run: `SECRET_KEY=test-only-key python manage.py check`

Expected: no issues.

- [ ] **Step 7: Suggested commit**

```bash
git add licencas portal/management/commands/sync_roles.py templates/partials/_sidebar.html
git commit -m "feat: add subscription management workflow"
```
