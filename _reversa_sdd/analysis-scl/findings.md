# Achados: SCL

## Requisitos
- Analisar o projeto iniciado em `C:\Users\leand\projetos\scl`.
- Preparar a futura migração da operação hoje concentrada no Django Admin para um portal próprio.
- Reutilizar o `design_system` já presente no projeto.
- Considerar `controlelicenca`, `ekklesiafiscal` e exclusivamente o LoteSis em `C:\Users\leand\projetos\lotesis` como referências.

## Achados iniciais
- Projeto acessível em `/mnt/c/Users/leand/projetos/scl`.
- Estrutura inicial contém `app/`, `licencas/`, `design_system/`, `data/`, `manage.py`, `db.sqlite3`, Docker e ambiente virtual.
- Não há `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` ou configuração Reversa dentro do projeto.
- A pasta não possui metadados Git.

## Arquitetura atual
- Django 5.0 monolítico, com pacote de projeto `app` e único app de domínio `licencas`.
- A raiz `/` aponta diretamente para o Django Admin com Jazzmin; não há portal, URLs do app, forms ou views implementadas.
- O domínio contém `Cliente`, `Sistema`, `ClienteSistema` e `AcessoMaquina`.
- O Admin registra `Cliente`, `Sistema` e `AcessoMaquina`; `ClienteSistema` não possui interface.
- A lógica do Admin limita-se a colunas, busca e filtros. Não foram encontradas regras de negócio customizadas em `admin.py`.
- Não há testes implementados.
- O banco efetivo nos settings é SQLite, enquanto o Compose provisiona PostgreSQL.

## Design system
- O diretório contém um catálogo HTML e uma referência Duralux estática, além dos assets compilados.
- Há shell, sidebar, header, cards, formulários, tabelas, filtros, paginação, estados, dark mode e responsividade.
- O material ainda não está integrado ao Django: não há `{% static %}`, herança de templates ou dados dinâmicos.
- Os assets incluem dependências antigas e versões divergentes de Bootstrap CSS/JS; a integração deve selecionar somente o necessário.
- O script de dashboard possui dados fictícios e não deve ser usado diretamente.

## Referências adotadas
- `controlelicenca`: arquitetura Django, autenticação, forms, services, URLs e estratégia de testes.
- `C:\Users\leand\projetos\lotesis`: shell Duralux, templates parciais, filtros, tabelas e paginação.
- `ekklesiafiscal`: matriz de papéis, escopo de dados e testes de isolamento.
- Não adotar SPA/React neste momento.

## Riscos confirmados
- `ClienteSistema.__str__()` retorna um objeto em vez de string.
- `AcessoMaquina.__str__()` retorna inteiro em vez de string.
- `AcessoMaquina.cliente` e `sistema` são IDs inteiros sem integridade referencial.
- `ClienteSistema` permite pares cliente/sistema duplicados.
- CNPJ/CPF não possui validação ou unicidade clara.
- Segredos e credenciais estão no código.
- Configurações SQLite, PostgreSQL, Celery e Docker estão incoerentes entre si.
- A pasta não possui Git e não há suíte de regressão para proteger a migração.

## Direção recomendada
- Portal server-rendered com Django Templates e JavaScript progressivo.
- Admin movido para `/admin/` e mantido temporariamente como fallback.
- Portal em `/portal/`, com URLs namespaced e permissões verificadas no servidor.
- Duralux isolado do Jazzmin, com `base.html`, `base_auth.html`, `base_app.html` e partials.
- Primeira entrega somente leitura antes dos CRUDs: shell, autenticação, dashboard e listagens.
- `ModelForm` para CRUD simples, selectors para consultas e services para mutações com regras.
