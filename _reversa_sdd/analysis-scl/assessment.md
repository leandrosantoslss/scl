# Diagnóstico inicial do SCL

## Resumo executivo

O SCL é um projeto Django 5.0 pequeno, hoje operado diretamente pelo Django Admin com Jazzmin. A migração para portal é viável sem reescrita: o código de domínio é reduzido, o `admin.py` não concentra regras customizadas e o projeto já possui um kit visual Duralux local. Seu domínio é próprio: cadastro de clientes e sistemas, assinatura por cliente-sistema, financeiro recorrente e validação diária de licença.

A direção recomendada é um portal Django server-rendered, mantendo o Admin temporariamente em `/admin/`. Projetos existentes servem apenas como referência técnica: não serão copiadas regras de negócio do `controlelicenca`. A experiência visual e os componentes devem seguir exclusivamente o LoteSis de `C:\Users\leand\projetos\lotesis`.

## Estado atual

### Aplicação

- Projeto Django: `app`.
- App de domínio: `licencas`.
- Rota atual: `/` aponta para `admin.site.urls` em `app/urls.py:21`.
- Banco efetivo: SQLite em `app/settings.py:78-82`.
- Interface: somente Django Admin/Jazzmin.
- Portal, API e views próprias: inexistentes.
- Testes: arquivo presente, sem casos implementados.

### Domínio

- `Cliente`: identificação, contato, endereço, status e timestamps.
- `Sistema`: nome, status e timestamps.
- `ClienteSistema`: associação entre cliente e sistema.
- `AcessoMaquina`: dados de acesso e máquina, com cliente/sistema armazenados como inteiros.

### Operações existentes

- Clientes: listagem, busca por nome/documento e filtros por nome/documento/status.
- Sistemas: listagem, busca por nome e filtros por nome/status.
- Acessos: listagem, busca por cliente/sistema e filtros por cliente/sistema/usuário.
- Associação cliente-sistema: modelo existente, mas sem tela no Admin.

## Design system

O diretório `design_system/` é uma referência visual estática, não um portal implementado. Ele oferece:

- shell com sidebar, topbar, breadcrumb e área de conteúdo;
- cards, métricas, tabelas, formulários, filtros e paginação;
- tema claro/escuro e comportamento responsivo;
- assets locais de Bootstrap, jQuery, ícones, SweetAlert e ApexCharts.

Para integrar ao Django será necessário:

1. Mover ou expor apenas os assets necessários via staticfiles.
2. Criar templates base e partials com `{% static %}` e `{% url %}`.
3. Substituir dados fictícios por contexto Django.
4. Carregar scripts de gráficos somente nas páginas que os utilizam.
5. Remover artefatos Cloudflare, links inexistentes e dependências sem uso.
6. Normalizar as versões divergentes de Bootstrap CSS e JavaScript.
7. Verificar a licença do tema antes de distribuição.

## Referências técnicas para o trabalho

### ControleLicença

Usar apenas como referência de organização técnica para:

- organização Django server-rendered;
- autenticação e sessão;
- forms, services e separação de responsabilidades;
- URLs e convivência entre portal e Admin;
- testes de autenticação, permissões e CRUD.

O domínio, os modelos financeiros e as regras de licença do ControleLicença não se aplicam ao SCL.

### LoteSis

Usar somente `C:\Users\leand\projetos\lotesis` (`/mnt/c/Users/leand/projetos/lotesis`) como referência para:

- integração do Duralux;
- `base.html`, `base_app.html` e partials;
- sidebar/topbar;
- filtros GET, tabelas responsivas e paginação;
- tokens e padrões visuais compartilhados.

Variantes como `lotesisweb`, `lotesis_old` e `lotesis-prototipo` ficam fora das decisões.

### EkklesiaFiscal

Usar como referência para:

- matriz de papéis e capacidades;
- escopo de dados por cliente/tenant;
- autorização no servidor além da ocultação de menus;
- testes de isolamento entre clientes.

## Problemas que antecedem o portal

### Críticos

- `ClienteSistema.__str__()` retorna um objeto `Cliente`, não uma string (`licencas/models.py:59-60`).
- `AcessoMaquina.__str__()` retorna inteiro (`licencas/models.py:81-82`).
- `AcessoMaquina` não possui FKs para cliente e sistema (`licencas/models.py:62-65`).
- Não existe restrição única para o par cliente/sistema.
- Segredos e credenciais estão versionados nos settings e no Compose.
- O banco autoritativo ainda precisa ser confirmado: settings usam SQLite e Docker sobe PostgreSQL.

### Estruturais

- Não há matriz explícita de permissões do portal.
- CNPJ/CPF não possui validação e formato definidos.
- Não há trilha do usuário responsável pelas alterações.
- Celery está configurado parcialmente e o Compose aponta para um módulo inexistente.
- O arquivo `Dockefile` não corresponde ao nome padrão esperado pelo Compose.
- Não há Git, CI, testes, health checks ou configuração por ambiente.

## Arquitetura-alvo inicial

```text
templates/
├── base.html
├── base_auth.html
├── base_app.html
├── partials/
│   ├── _sidebar.html
│   ├── _topbar.html
│   ├── _messages.html
│   ├── _filters.html
│   └── _pagination.html
└── portal/
    ├── dashboard.html
    ├── clientes/
    ├── sistemas/
    ├── cliente_sistemas/
    └── acessos/

static/
├── vendor/duralux/
├── css/
└── js/
```

Camadas Python recomendadas:

- views finas para HTTP;
- `ModelForm` para entrada e validação de CRUD;
- selectors para filtros, paginação e consultas compostas;
- services para concessão/revogação e mutações transacionais;
- permissions/decorators ou mixins reutilizáveis;
- repositório apenas se houver banco externo, não como wrapper do ORM.

## Sequência recomendada

1. Confirmar banco autoritativo, regras de licença e matriz de papéis.
2. Criar testes de caracterização dos modelos e operações atuais.
3. Corrigir integridade e modelagem prioritárias com migrações controladas.
4. Externalizar segredos e alinhar configurações de ambiente.
5. Criar shell Duralux, login e rotas `/portal/`, preservando o Admin em `/admin/`.
6. Entregar dashboard e listagens somente leitura com filtros e paginação.
7. Implementar CRUD de Cliente e Sistema.
8. Implementar gestão de `ClienteSistema` com unicidade e regras de ativação.
9. Tratar acessos de máquina inicialmente como consulta/auditoria.
10. Migrar usuários gradualmente e restringir o Admin a superusuários.

## Decisões ainda necessárias

1. Qual banco contém os dados válidos hoje: SQLite ou PostgreSQL?
2. Quais papéis existirão no portal e quais dados cada papel poderá acessar?
3. O que define uma licença válida: vínculo ativo, vigência, quantidade de máquinas, chave ou outro critério?
4. Os IDs de cliente e sistema em `AcessoMaquina` são IDs locais ou vêm de sistemas externos?
5. A primeira entrega deve começar pelo shell/autenticação ou incluir imediatamente a lista de clientes?
