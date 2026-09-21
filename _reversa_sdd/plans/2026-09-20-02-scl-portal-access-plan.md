# SCL Portal and Access Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar um portal Duralux autenticado, com navegação, papéis internos e Admin restrito a superusuários.

**Architecture:** Criar o app `portal` para autenticação, dashboard e autorização compartilhada. Servir o Duralux existente por alias de staticfiles, sem copiar nem editar os arquivos minificados.

**Tech Stack:** Django Templates, Django auth/groups/permissions, Bootstrap/Duralux, pytest-django.

**Spec:** `_reversa_sdd/specs/2026-09-20-scl-licenciamento-financeiro-design.md`

## Global Constraints

- Seguir a composição visual de `C:\Users\leand\projetos\lotesis`, não suas regras de negócio.
- Usar `{% url %}`; não adicionar links literais para páginas internas.
- Logout e toda mutação usam POST com CSRF.
- Admin fica em `/admin/` e aceita apenas superusuários.
- Permissões são verificadas no servidor; esconder menu não é autorização.
- Commits somente com Git inicializado e autorização do usuário.

---

### Task 1: Portal App, Authentication, and Routes

**Files:**
- Create: `portal/__init__.py`
- Create: `portal/apps.py`
- Create: `portal/views.py`
- Create: `portal/urls.py`
- Create: `portal/tests/__init__.py`
- Create: `portal/tests/conftest.py`
- Create: `portal/tests/test_auth.py`
- Create: `templates/portal/home.html`
- Create: `templates/registration/login.html`
- Modify: `app/settings.py`
- Modify: `app/urls.py`

**Interfaces:**
- Produces: URL names `login`, `logout`, `portal:home`.
- Produces: authenticated portal at `/portal/`; root redirects there.

- [ ] **Step 1: Write authentication route tests**

Define `csrf_client` as `django.test.Client(enforce_csrf_checks=True)`. In addition to the tests below, authenticate that client and assert `POST /logout/` without a CSRF token returns `403`; obtain a token from a rendered form and assert the valid POST succeeds.

```python
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse


def test_anonymous_portal_redirects_to_login(client):
    response = client.get(reverse("portal:home"))
    assert response.status_code == 302
    assert reverse("login") in response["Location"]


@pytest.mark.django_db
def test_authenticated_user_opens_portal(client):
    user = get_user_model().objects.create_user("operator", password="secret")
    client.force_login(user)
    assert client.get(reverse("portal:home")).status_code == 200


@pytest.mark.django_db
def test_logout_requires_post(client):
    user = get_user_model().objects.create_user("operator", password="secret")
    client.force_login(user)
    assert client.get(reverse("logout")).status_code == 405
    assert client.post(reverse("logout")).status_code == 302
```

- [ ] **Step 2: Verify route tests fail**

Run: `SECRET_KEY=test-only-key python -m pytest portal/tests/test_auth.py -v`

Expected: collection or reverse failure because the app and routes do not exist.

- [ ] **Step 3: Implement portal views, URLs, and minimal templates**

```python
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def home(request):
    return render(request, "portal/home.html")
```

Use Django `LoginView` and `LogoutView`; configure logout for POST only with a small subclass that returns `HttpResponseNotAllowed` on GET. Create minimal valid login/home templates in this task; the home template includes a CSRF-protected logout form. Task 2 replaces their markup with the Duralux shell. Password reset is outside the approved route contract and is not added here.

- [ ] **Step 4: Configure sessions and redirects**

Add:

```python
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/portal/"
LOGOUT_REDIRECT_URL = "/login/"
SESSION_COOKIE_AGE = 1800
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
```

- [ ] **Step 5: Run auth tests**

Run: `SECRET_KEY=test-only-key python -m pytest portal/tests/test_auth.py -v`

Expected: all tests pass.

- [ ] **Step 6: Suggested commit**

```bash
git add portal app/settings.py app/urls.py templates/portal/home.html templates/registration/login.html
git commit -m "feat: add authenticated portal entrypoint"
```

### Task 2: Duralux Template Shell

**Files:**
- Create: `templates/base.html`
- Create: `templates/base_app.html`
- Create: `templates/base_auth.html`
- Create: `templates/partials/_sidebar.html`
- Create: `templates/partials/_topbar.html`
- Create: `templates/partials/_messages.html`
- Modify: `templates/portal/home.html`
- Modify: `templates/registration/login.html`
- Create: `static/css/tokens.css`
- Create: `static/css/portal.css`
- Create: `static/js/portal.js`
- Create: `portal/tests/test_shell.py`
- Modify: `app/settings.py`

**Interfaces:**
- Produces: template blocks `title`, `body`, `page_title`, `breadcrumb`, `page_actions`, `content`, `extra_css`, `extra_js`.
- Produces: static prefix `vendor/duralux/...` backed by `design_system/refs/duralux`.

- [ ] **Step 1: Write failing shell and static tests**

```python
import pytest
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.urls import reverse


def test_duralux_assets_are_discoverable():
    assert finders.find("vendor/duralux/css/theme.min.css")
    assert finders.find("vendor/duralux/js/common-init.min.js")


@pytest.mark.django_db
def test_portal_uses_accessible_application_shell(client):
    user = get_user_model().objects.create_user("viewer", password="secret")
    client.force_login(user)
    content = client.get(reverse("portal:home")).content.decode()
    assert 'aria-label="Navegação principal"' in content
    assert "nxl-container" in content
    assert "Dashboard" in content
```

- [ ] **Step 2: Verify tests fail**

Run: `SECRET_KEY=test-only-key python -m pytest portal/tests/test_shell.py -v`

Expected: assets/templates are not found.

- [ ] **Step 3: Configure template and static directories**

```python
TEMPLATES[0]["DIRS"] = [BASE_DIR / "templates"]
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    BASE_DIR / "static",
    ("vendor/duralux", BASE_DIR / "design_system" / "refs" / "duralux"),
]
```

- [ ] **Step 4: Build the base document**

Load only:

```django
{% load static %}
<link rel="stylesheet" href="{% static 'vendor/duralux/css/bootstrap.min.css' %}">
<link rel="stylesheet" href="{% static 'vendor/duralux/css/vendors.min.css' %}">
<link rel="stylesheet" href="{% static 'vendor/duralux/css/theme.min.css' %}">
<link rel="stylesheet" href="{% static 'css/tokens.css' %}">
<link rel="stylesheet" href="{% static 'css/portal.css' %}">
```

Load `vendors.min.js`, `common-init.min.js` and `portal.js` at the end of body. Do not load demo dashboard data, Cloudflare scripts, daterangepicker or charts globally.

- [ ] **Step 5: Build application and authentication shells**

Follow the semantic structure:

```django
{% extends "base.html" %}
{% block body %}
  {% include "partials/_sidebar.html" %}
  {% include "partials/_topbar.html" %}
  <main class="nxl-container">
    <div class="nxl-content">
      <header class="page-header">...</header>
      <div class="main-content">
        {% include "partials/_messages.html" %}
        {% block content %}{% endblock %}
      </div>
    </div>
  </main>
{% endblock %}
```

Use `logo-full.png` and `logo-abbr.png` from the vendor alias with meaningful alt text.

- [ ] **Step 6: Run shell tests**

Run: `SECRET_KEY=test-only-key python -m pytest portal/tests/test_shell.py -v`

Expected: all tests pass.

- [ ] **Step 7: Suggested commit**

```bash
git add templates static portal/tests/test_shell.py app/settings.py
git commit -m "feat: integrate duralux portal shell"
```

### Task 3: Internal Roles and Server-Side Authorization

**Files:**
- Create: `portal/roles.py`
- Create: `portal/permissions.py`
- Create: `portal/management/__init__.py`
- Create: `portal/management/commands/__init__.py`
- Create: `portal/management/commands/sync_roles.py`
- Create: `portal/tests/test_roles.py`

**Interfaces:**
- Produces: role constants `ADMINISTRADOR`, `CADASTRO`, `FINANCEIRO`, `CONSULTA`.
- Produces: `sync_roles()` and `group_required(*group_names)`.

- [ ] **Step 1: Write failing idempotency and authorization tests**

```python
import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command

from portal.roles import ADMINISTRADOR, CADASTRO, CONSULTA, FINANCEIRO


@pytest.mark.django_db
def test_sync_roles_is_idempotent():
    call_command("sync_roles")
    call_command("sync_roles")
    assert set(Group.objects.values_list("name", flat=True)) >= {
        ADMINISTRADOR,
        CADASTRO,
        FINANCEIRO,
        CONSULTA,
    }
```

- [ ] **Step 2: Verify the command test fails**

Run: `SECRET_KEY=test-only-key python -m pytest portal/tests/test_roles.py -v`

Expected: import or command failure.

- [ ] **Step 3: Implement role synchronization**

Create groups with `get_or_create`. Assign existing `licencas` permissions as follows:

```python
ROLE_PERMISSION_PREFIXES = {
    ADMINISTRADOR: ("add_", "change_", "delete_", "view_"),
    CADASTRO: ("add_", "change_", "view_"),
    FINANCEIRO: ("view_",),
    CONSULTA: ("view_",),
}
```

The command must clear and reapply only permissions owned by SCL apps, leaving unrelated permissions untouched.

- [ ] **Step 4: Implement reusable authorization**

```python
from functools import wraps
from django.core.exceptions import PermissionDenied


def group_required(*names):
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            allowed = request.user.is_superuser or request.user.groups.filter(name__in=names).exists()
            if not allowed:
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapped
    return decorator
```

- [ ] **Step 5: Run role tests**

Run: `SECRET_KEY=test-only-key python -m pytest portal/tests/test_roles.py -v`

Expected: all tests pass.

- [ ] **Step 6: Suggested commit**

```bash
git add portal/roles.py portal/permissions.py portal/management portal/tests/test_roles.py
git commit -m "feat: add internal portal roles"
```

### Task 4: Durable Domain Audit Trail

**Files:**
- Create: `portal/models.py`
- Create: `portal/audit.py`
- Create: `portal/migrations/__init__.py`
- Create: migrations in `portal/migrations/`
- Create: `portal/tests/test_audit.py`
- Create: `portal/views_audit.py`
- Create: `templates/portal/audit/list.html`
- Create: `templates/portal/audit/detail.html`
- Create: `portal/tests/test_audit_views.py`
- Modify: `portal/urls.py`
- Modify: `templates/partials/_sidebar.html`

**Interfaces:**
- Produces: immutable `EventoAuditoria` and `registrar_evento_auditoria(...) -> EventoAuditoria`.
- Produces: sanitized `/portal/auditoria/` list/detail views.

- [ ] **Step 1: Write failing audit tests**

Cover actor and integration/system origins, action, object label/ID, sanitized before/after JSON, reason, request ID and timestamp. Assert secret, token, authorization and raw document fields are rejected/redacted. Assert application services never update or delete an event.

- [ ] **Step 2: Implement the append-only audit model**

Fields: UUID `public_id`, nullable human actor, `origem` (`portal`, `integration`, `system`), nullable origin identifier, `acao`, `objeto_tipo`, `objeto_id`, sanitized `antes`/`depois` JSON, `motivo`, nullable request ID and `criado_em`. Default model manager exposes creation/read only. Read-only Admin registration is deferred to Task 5, where `app/admin.py` exists.

- [ ] **Step 3: Implement transactional recording**

Domain services call `registrar_evento_auditoria` inside the same `transaction.atomic()` as the mutation. Use an explicit allowlist serializer; never pass model `__dict__` or request headers. Audit creation failure must roll back the business mutation rather than leave an unaudited sensitive change.

- [ ] **Step 4: Implement portal audit views and run tests**

Implement paginated sanitized portal views. Administrador sees all sanitized events; Financeiro and Consulta can read sanitized audit; Cadastro sees only client/system/subscription events and never financial, integration or credential before/after values. No role sees secrets, authorization data or raw documents. Add server-side permission tests and CSRF-safe read-only routing.

Run: `SECRET_KEY=test-only-key python -m pytest portal/tests/test_audit.py portal/tests/test_audit_views.py -v`

Expected: PASS.

- [ ] **Step 5: Suggested commit**

```bash
git add portal/models.py portal/audit.py portal/views_audit.py portal/urls.py portal/migrations portal/tests/test_audit.py portal/tests/test_audit_views.py templates/portal/audit templates/partials/_sidebar.html
git commit -m "feat: add immutable domain audit trail"
```

### Task 5: Superuser-Only Admin and Dashboard Gate

**Files:**
- Create: `app/admin.py`
- Modify: `app/urls.py`
- Modify: `licencas/admin.py`
- Modify: `portal/views.py`
- Modify: `templates/portal/home.html`
- Create: `portal/tests/test_admin_access.py`
- Create: `portal/tests/test_dashboard.py`

**Interfaces:**
- Produces: `admin_site` with `has_permission()` restricted to active superusers.
- Produces: dashboard counters `clientes_total`, `sistemas_total`, `assinaturas_total`.

- [ ] **Step 1: Write failing Admin permission tests**

```python
import pytest
from django.contrib.auth import get_user_model


@pytest.mark.django_db
def test_staff_non_superuser_cannot_access_admin(client):
    user = get_user_model().objects.create_user("staff", password="secret", is_staff=True)
    client.force_login(user)
    assert client.get("/admin/").status_code in {302, 403}


@pytest.mark.django_db
def test_superuser_can_access_admin(client):
    user = get_user_model().objects.create_superuser("root", "root@example.com", "secret")
    client.force_login(user)
    assert client.get("/admin/").status_code == 200
```

- [ ] **Step 2: Verify the non-superuser test fails**

Run: `SECRET_KEY=test-only-key python -m pytest portal/tests/test_admin_access.py -v`

Expected: current default Admin accepts staff users.

- [ ] **Step 3: Create and use the restricted AdminSite**

```python
from django.contrib.admin import AdminSite


class SuperuserAdminSite(AdminSite):
    def has_permission(self, request):
        return request.user.is_active and request.user.is_superuser


admin_site = SuperuserAdminSite(name="scl_admin")
```

Register `User`, `Group`, `Cliente`, `Sistema`, `ClienteSistema` and `AcessoMaquina` on this site. Route `path("admin/", admin_site.urls)`.

Register `EventoAuditoria` read-only: disable add/change/delete and expose only sanitized fields to active superusers.

- [ ] **Step 4: Add tested dashboard counters**

The view should query only counts and render three Duralux metric cards. Test exact values with factories or direct model creation.

- [ ] **Step 5: Run the portal gate**

Run: `SECRET_KEY=test-only-key python -m pytest portal -v`

Expected: all portal tests pass.

Run: `SECRET_KEY=test-only-key python manage.py check`

Expected: no issues.

- [ ] **Step 6: Suggested commit**

```bash
git add app/admin.py app/urls.py licencas/admin.py portal templates/portal/home.html
git commit -m "feat: enforce portal roles and superuser admin"
```
