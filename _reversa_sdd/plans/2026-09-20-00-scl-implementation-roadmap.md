# SCL Implementation Roadmap

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar o SCL em incrementos testáveis, do saneamento da base até o portal, financeiro, integrações legadas e licenciamento.

**Architecture:** Monólito modular Django com os apps existentes preservados e novos apps `portal`, `financeiro`, `integracoes` e `licenciamento`. Todos os canais chamam os mesmos serviços de domínio; PostgreSQL é a fonte de verdade de produção.

**Tech Stack:** Python 3.11+, Django 5.2 LTS, PostgreSQL 16, Django REST Framework, OAuth2 Client Credentials, JWT RS256, pytest/pytest-django, Bootstrap/Duralux.

**Spec:** `_reversa_sdd/specs/2026-09-20-scl-licenciamento-financeiro-design.md`

## Global Constraints

- Não editar o legado até o usuário criar `.reversa/reversa-config.json` com `allowLegacyEdits: true` e liberar os caminhos necessários.
- Nunca criar nem alterar `.reversa/reversa-config.json` pela automação.
- Produção usa PostgreSQL; SQLite pode ser usado apenas em testes unitários que não dependam de comportamento específico do PostgreSQL.
- Timezone operacional: `America/Sao_Paulo`.
- Dia de vencimento permitido: 1 a 28.
- Sem Celery na primeira implementação; geração recorrente usa management command idempotente.
- Sem MD5; tokens de licença usam RS256 e expiram no início do próximo dia operacional.
- API de licenciamento e API administrativa usam credenciais, modelos e rate limits separados.
- Lotes administrativos aceitam no máximo 100 itens.
- O sistema legado sempre inicia a integração; o SCL não faz polling nem envia webhooks de saída nessa versão.
- Efí, Sicredi e Sicoob exigem specs técnicas próprias antes de seus adaptadores serem implementados.
- O diretório não possui Git. Só executar passos de commit depois de o usuário inicializar o repositório e autorizar commits.
- Antes de qualquer `migrate` ou mutação de dados, identificar e registrar o banco autoritativo, exigir URL explícita, confirmar o alvo diretamente com o cliente PostgreSQL e concluir o Gate 0 de backup/restauração do Plano 01.

## Required Edit Permission

Antes da execução, o usuário deve liberar ao menos os caminhos abaixo. Este bloco é orientação; o agente não deve escrevê-lo por conta própria.

```json
{
  "allowLegacyEdits": true,
  "allowedPaths": [
    "app/**",
    "licencas/**",
    "portal/**",
    "financeiro/**",
    "integracoes/**",
    "licenciamento/**",
    "tests/**",
    "templates/**",
    "static/**",
    "requirements.txt",
    "pytest.ini",
    "Dockerfile",
    "Dockefile",
    "docker-compose.yml",
    ".dockerignore",
    ".env.example"
  ]
}
```

## Target File Structure

```text
app/
├── settings.py
└── urls.py
licencas/
├── forms/
├── services/
├── selectors.py
├── templates/licencas/
├── tests/
├── urls.py
├── validators.py
└── views/
portal/
├── templates/portal/
├── tests/
├── urls.py
└── views.py
financeiro/
├── gateways/
├── management/commands/
├── services/
├── templates/financeiro/
├── tests/
├── models.py
└── urls.py
integracoes/
├── api/
├── services/
├── tests/
└── models.py
licenciamento/
├── api/
├── services/
├── tests/
└── models.py
templates/
├── base.html
├── base_app.html
├── base_auth.html
└── partials/
static/
├── css/
└── js/
```

## Plan Sequence

1. `_reversa_sdd/plans/2026-09-20-01-scl-foundation-plan.md`
2. `_reversa_sdd/plans/2026-09-20-02-scl-portal-access-plan.md`
3. `_reversa_sdd/plans/2026-09-20-03-scl-cadastros-assinaturas-plan.md`
4. `_reversa_sdd/plans/2026-09-20-04-scl-financeiro-manual-plan.md`
5. `_reversa_sdd/plans/2026-09-20-05-scl-integracoes-legadas-plan.md`
6. `_reversa_sdd/plans/2026-09-20-06-scl-licenciamento-plan.md`
7. `_reversa_sdd/plans/2026-09-20-07-scl-gateway-core-plan.md`
8. Specs e planos separados dos adaptadores Efí, Sicredi e Sicoob, após acesso às documentações e credenciais de homologação.
9. `_reversa_sdd/plans/2026-09-20-08-scl-hardening-rollout-plan.md`

## Dependency Graph

```text
01 Foundation
  └── 02 Portal
      └── 03 Cadastros e assinaturas
          ├── 04 Financeiro manual
          │   ├── 05 Integrações legadas
          │   ├── 06 Licenciamento
          │   └── 07 Gateway core
          │       ├── Adaptador Efí
          │       ├── Adaptador Sicredi
          │       └── Adaptador Sicoob
          └──────────────────────────────┐
                                         └── 08 Hardening e rollout
```

## Release Gates

- **Gate A:** fundação, checks e testes verdes.
- **Gate B:** portal autenticado e permissões verificadas no servidor.
- **Gate C:** CRUD e assinatura funcionando sem Admin.
- **Gate D:** cobranças e pagamentos manuais determinísticos.
- **Gate E:** integração legada idempotente e sem geração duplicada.
- **Gate F:** licença diária, carência e token RS256 validados.
- **Gate G:** contrato comum de gateways aprovado.
- **Gate H:** planos e implementações dos três adaptadores concluídos; Efí, Sicredi e Sicoob homologados em sandbox e produção para cada meio efetivamente habilitado no respectivo convênio (boleto, PIX ou ambos).
- **Gate I:** segurança, observabilidade, carga e migração gradual aprovadas.

## Commit Policy

Cada plano sugere commits Conventional Commits. Se o usuário ainda não tiver inicializado Git ou não tiver solicitado commits, execute a verificação e registre o marco em `_reversa_sdd/analysis-scl/progress.md`, sem rodar `git commit`.
