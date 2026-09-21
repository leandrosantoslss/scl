# Progresso: diagnóstico inicial do SCL

## Sessão 2026-09-20

### Estado
- **Fase:** 6 - Planejamento de implementação
- **Status:** concluído

### Ações
- Localizado o projeto no caminho WSL correspondente ao caminho Windows informado.
- Confirmada a estrutura raiz inicial.
- Verificada a ausência de instruções locais e de repositório Git.
- Mapeados arquitetura Django, domínio, Admin, configurações, infraestrutura e lacunas de teste.
- Inventariado o design system Duralux e sua prontidão para integração com Django Templates.
- Comparados os padrões de `controlelicenca`, `ekklesiafiscal` e do LoteSis canônico em `C:\Users\leand\projetos\lotesis`.
- Consolidado o diagnóstico em `assessment.md`.
- Redefinido o domínio como cadastro, assinatura cliente-sistema, financeiro recorrente e licenciamento diário.
- Aprovadas em conversa as decisões de arquitetura, dados, financeiro, API, portal, segurança e entrega.
- Criada e autorrevisada a especificação `_reversa_sdd/specs/2026-09-20-scl-licenciamento-financeiro-design.md`.
- Revisada a arquitetura financeira para cadastro multi-conta de Efí, Sicredi e Sicoob, com escolha por cobrança e suporte a boleto/PIX.
- Adicionada API administrativa para legados consultarem e alimentarem clientes, assinaturas, cobranças e pagamentos.
- Definidas autoridade configurável, referências externas, OAuth2, idempotência, conflitos por versão e cargas em lote.
- Recebida a aprovação final do usuário para a especificação.
- Criados o roadmap e oito planos executáveis em `_reversa_sdd/plans/`.
- Executadas três passagens de revisão cruzada dos planos contra a especificação.
- Corrigidos o Gate 0 de PostgreSQL/backup, a migração sem desativação silenciosa, a trilha de auditoria, a autoridade do legado no portal, a rotação sobreposta de credenciais e a proveniência financeira.
- Fechados contratos de gateway para timeout ambíguo, reconciliação, webhooks idempotentes, URLs seguras e teste de conexão.
- Tornados executáveis os gates de CSRF, throttling compartilhado, concorrência PostgreSQL, carga, segurança HTTP, scheduler, healthcheck e rollout.
- Mantido o código legado sem alterações; somente artefatos em `_reversa_sdd/` foram modificados.

### Verificações
| Verificação | Resultado |
|---|---|
| Acesso ao projeto | OK |
| Estado Git | Não aplicável: diretório sem `.git` |
| Alterações no legado | Nenhuma |
| Diagnóstico arquitetural | Concluído |
| Inventário do design system | Concluído |
| Comparação das referências | Concluída |
| Especificação de licenciamento e financeiro | Aprovada pelo usuário |
| Roadmap e oito planos | Criados e autorrevisados |
| Achados críticos remanescentes nos planos | Nenhum após a revisão final |
| Código legado alterado | Não |
| Liberação para editar o legado | Pendente de `.reversa/reversa-config.json` pelo usuário |
| Adaptadores Efí/Sicredi/Sicoob | Bloqueados até documentação, planos e homologação |

### Erros
| Erro | Tratamento |
|---|---|
| `git status` e `git diff --stat` falharam por ausência de repositório | Continuar diagnóstico sem histórico de alterações |
| Patch inicial da revisão de gateways falhou por contexto divergente | Nenhuma alteração parcial ocorreu; revisão aplicada em blocos menores |
| `sqlite3` não está disponível no ambiente | Contagens do banco local obtidas com a biblioteca padrão do Python |

## Execução do Plano 01

### Task 0 - Gate de pré-migração

- Configuração Reversa validada com edição irrestrita liberada pelo usuário.
- Trabalho em worktree indisponível porque o diretório não possui Git; nenhum commit será executado.
- Operador selecionou PostgreSQL externo como banco autoritativo.
- Operador decidiu preservar `AcessoMaquina` como histórico.
- SQLite local confirmado com zero linhas nas quatro tabelas do domínio.
- Diretório PostgreSQL legado `data/db/` mantido intocado e classificado como não autoritativo.
- Criados `.env` local com placeholders e `.gitignore` para impedir versionamento de segredos/dados locais.
- Ambiente sem `psql`, `pg_dump` e Docker ativo; Python do Windows possui `psycopg2` para inspeção somente leitura.
- Uma linha do `.env` foi exibida acidentalmente em log de sessão; o operador rotacionou a credencial exposta antes da validação.
- Bancos `DBSCL` (autoritativo) e `SCL_TEST_DB` (testes descartáveis) criados vazios no PostgreSQL 17.11 externo via script idempotente.
- Validação somente leitura confirmou servidor `17.11`, schema público vazio nos dois bancos e nomes distintos entre alvo e testes.
- Backup `pg_dump` registrado como não aplicável para bancos recém-criados vazios; obrigatório antes do primeiro deploy com dados reais.
- **Gate 0 fechado com aprovação do operador**; runbook `_reversa_sdd/runbooks/pre-migration-gate.md` atualizado com evidência completa.

### Task 1 - Test harness e configuração de ambiente

- `requirements.txt` reescrito com dependências diretas (Django 5.2, django-environ, jazzmin, psycopg, pytest, pytest-django, dateutil).
- `pytest.ini` criado com `app.settings`.
- Testes de configuração escritos primeiro; vermelho confirmado (2 falhas: chave scaffold e senha literal).
- `app/settings.py` migrado para leitura de ambiente com `django-environ`; credenciais literais de PostgreSQL e `CELERY_BROKER_URL` removidos.
- `.env.example` criado sem segredos reais.
- `SECRET_KEY=test-only-key DEBUG=true python -m pytest tests/test_settings.py -v` → **3 passed**.

### Task 2 - Baseline de containers e PostgreSQL

- Testes de configuração de container escritos primeiro; vermelho confirmado (2 falhas: serviços extras e Dockerfile ausente).
- `Dockefile` (typo) removido; `Dockerfile` production-shaped criado (python:3.11-slim, usuário não-root).
- `docker-compose.yml` reescrito: apenas `db` (postgres:16-alpine, volume nomeado `postgres_data`, healthcheck `pg_isready`) e `web` (env_file configurável, depends_on healthy, healthcheck `/health/` com header de proxy); sem RabbitMQ/Celery e sem migrate automático.
- `.dockerignore` criado protegendo `.env`, `data/`, `db.sqlite3` e artefatos locais.
- `PyYAML>=6,<7` adicionado às dependências de teste.
- `python -m pytest tests/test_container_config.py -v` → **2 passed**.
- Bloqueio de ambiente: `docker compose config` não executado porque Docker Desktop não está ativo; validação estrutural coberta pelos testes e revalidação de Compose registrada como pendente para quando o Docker estiver disponível.

### Task 3 - Caracterização e reparo dos modelos existentes

- `licencas/tests.py` removido; pacote `licencas/tests` criado com `test_legacy_models.py`.
- Vermelho confirmado: `__str__` de `ClienteSistema` retornava objeto e de `AcessoMaquina` retornava inteiro.
- `__str__` corrigidos para strings determinísticas.
- Drift de metadados detectado e corrigido com `0004_alter_acessomaquina_options.py` (apenas `AlterModelOptions`; nenhuma tabela é dropada ou recriada).
- Incidente registrado: a primeira execução `django_db` usou `DATABASE_URL` do `.env` e criou/destruiu `test_DBSCL` no cluster autoritativo; sem impacto em dados, e a partir de então toda execução com banco usa `SCL_TEST_DATABASE_URL` via `run-tests.ps1`/`run-manage.ps1` com alvo explícito.

### Task 4 - Health endpoint e gate final da fundação

- `app/health.py` criado com probe de banco; rota `/health/` adicionada em `app/urls.py`.
- Teste de health escrito primeiro; vermelho confirmado; implementação verde.
- **Gate A fechado**: suíte completa `python -m pytest` → **8 passed** no banco descartável; `manage.py check` → nenhum issue.

## Execução do Plano 02

### Task 1 - App portal, autenticação e rotas

- App `portal` criado; rotas `/login/`, `/logout/` (POST-only via `LogoutPOSTView`) e `/portal/` (namespace `portal:home`).
- `csrf_client` com `enforce_csrf_checks=True` em `portal/tests/conftest.py`; testes cobrem redirect anônimo, portal autenticado, logout POST-only, rejeição `403` sem token CSRF e sucesso com token válido.
- Templates mínimos criados (login com `{% csrf_token %}` e home com formulário de logout protegido); markup Duralux fica para a Task 2.
- `app/settings.py`: app `portal`, `DIRS` de templates, redirects de login/logout e política de sessão (idade 1800, httpOnly, SameSite Lax, secure quando não-DEBUG).
- Vermelho confirmado (5 falhas) → verde: `portal/tests/test_auth.py` → **5 passed**.
- Suíte completa → **13 passed**. Password reset deliberadamente fora do contrato de rotas aprovado.

### Task 2 - Shell de templates Duralux

- `STATIC_URL`, `STATIC_ROOT` e `STATICFILES_DIRS` com alias `vendor/duralux` para `design_system/refs/duralux` declarado via `os.path.join`.
- `base.html` carrega apenas Bootstrap/vendors/theme + tokens.css/portal.css; `vendors.min.js`, `common-init.min.js` e `portal.js` no fim do body; sem demos, Cloudflare, daterangepicker ou charts globais.
- `base_app.html` (sidebar/topbar/page-header/content), `base_auth.html`, partials `_sidebar` (aria-label, logos com alt), `_topbar` (logout POST com CSRF) e `_messages`.
- `tokens.css`, `portal.css` e `portal.js` criados como camadas próprias do portal; login e home agora estendem os shells.
- Dever do ambiente registrado: Django 5.2 `FileSystemFinder.find_location` casa o prefixo com `os.sep`; no Windows a busca por caminhos com '/' retorna None. Alias e testes adaptados com `os.path.join` nativo; URLs renderizadas e `collectstatic` (Linux/container) preservam o comportamento do plano.
- Vermelho confirmado (2 falhas) → verde: `portal/tests` → **7 passed**; suíte completa → **15 passed**.

### Task 3 - Papéis internos e autorização server-side

- `portal/roles.py` com `ADMINISTRADOR`, `CADASTRO`, `FINANCEIRO`, `CONSULTA` e mapeamento de prefixos.
- Comando `sync_roles` idempotente: cria grupos com `get_or_create` e reaplica apenas permissões dos apps SCL (`licencas`, `portal`, `financeiro`, `integracoes`, `licenciamento`).
- `portal/permissions.py` com `group_required` (superusuário ou membro do grupo; `PermissionDenied` caso contrário).
- Vermelho por comando inexistente → verde: `test_roles.py` → **5 passed** (idempotência, prefixos, membro/não-membro/superusuário).

### Task 4 - Trilha de auditoria durável

- `portal/models.py` com `EventoAuditoria` append-only: `save()` rejeita atualização, `delete()` do modelo e do manager rejeitam exclusão.
- `portal/audit.py` com `registrar_evento_auditoria(...)` e política de mascaramento: valores sob chaves sensíveis (token, client_secret, authorization, senha, password, secret, document, cnpjcpf, cpf, credencial) são gravados como `[REDACTED]` (decisão: redact em vez de reject, mesma proteção do plano).
- Migração `portal/0001_initial` criada.
- `portal/views_audit.py` com matriz de papéis: Administrador/superusuário tudo; Cadastro restrito a objetos de licencas (cliente/sistema/assinatura); Financeiro e Consulta leem auditoria sanitizada; anônimo cai em login.
- `/portal/auditoria/` e `/portal/auditoria/<uuid>/` com templates Duralux e link na sidebar.
- Vermelho → verde: `test_audit.py` (7) + `test_audit_views.py` (5) → **12 passed**.

### Task 5 - Admin restrito a superusuários e dashboard

- `app/admin_site.py` com `SuperuserAdminSite.has_permission` (ativo + superusuário); User/Group registrados no novo site.
- `licencas/admin.py` migrado para `admin_site` (Cliente, Sistema, AcessoMaquina, ClienteSistema); `/admin/` roteado para o site restrito; AdminSite padrão mantido importado somente como contingência.
- Dashboard com contadores `clientes_total`, `sistemas_total`, `assinaturas_total` renderizados como três cards Duralux.
- Vermelho confirmado (staff entrava no Admin) → verde: `test_admin_access.py` (2) + `test_dashboard.py` (1).
- **Gate B fechado**: suíte completa → **36 passed**; `manage.py check` → nenhum issue; portals protegidos por login, CSRF testado e papéis verificados no servidor.

## Execução do Plano 03

### Task 1 - Validators de documento e auditoria de dados legados

- `python-stdnum>=1.20,<2` adicionado e instalado.
- `licencas/validators.py`: `normalize_document` + `validate_document`.
- Descoberta registrada: `stdnum.br.cpf.is_valid` aceita "11111111111" (checksum válido); regra brasileira clássica aplicada — dígitos repetidos/valor com tamanho inválido são rejeitados.
- `audit_legacy_data` somente leitura com contagens `invalid_documents`, `duplicate_documents`, `duplicate_client_system_pairs` e `CommandError` em qualquer contagem não nula.
- Vermelho (import + validação) → verde: validators + command → **7 passed** no banco descartável.
- Auditoria no alvo autoritativo (`run-manage.ps1 -Authoritative audit_legacy_data`) marcada como pendente: o banco `DBSCL` ainda não possui tabelas porque nenhuma migração foi aplicada nele; executar imediatamente após `migrate` nas Tasks 2-3.

### Task 2 - Evoluir Cliente e Sistema com segurança

- Testes primeiro; vermelho confirmado (6 falhas por campos ausentes).
- `Cliente`: `cnpjcpf` único com normalização em `clean()`/`save()`, validação, `bloqueado`/`motivo_bloqueio`/`bloqueado_em` e regra do motivo obrigatório.
- `Sistema`: `codigo` único e `descricao`; código tratado como imóvel após criação (regressão testada nos services/forms da Task 4).
- Migração defensiva em três passos: `0005` (campos novos, sem unique), `0006` (normaliza documentos com aborto por colisão e popula `codigo` por slug mais PK), `0007` (constraints finais de unique).
- Desvio registrado: `cnpjcpf` final usa `max_length=18` porque `full_clean` valida comprimento antes de `clean()` com valor mascarado; o banco continua armazenando dígitos normalizados (14/11).
- `test_audit_command` adaptado: duplicidade de documento/par agora é atributo do schema (IntegrityError) e o comando guarda papel de defesa em profundidade para janela pré-constraint.
- Migrações aplicadas no banco descartável e no autoritativo; suíte completa → **50 passed** na Task 2.

### Task 3 - ClienteSistema como assinatura

- `Periodicidade` (monthly/quarterly/semiannual/annual), `valor_recorrente`, `periodicidade`, `data_inicio`, `data_fim`, `primeiro_vencimento`, bloqueio com motivo, `dia_vencimento` (1-28, nulo) e `dias_carencia` (não negativa).
- Constraints: par `(cliente, sistema)` único, dia entre 1-28, carência não negativa e valor positivo quando ativa; `clean()` reforça as validações.
- Migrações em três passos escrevendo `ativo` jamais: `0008` schema nullable + par único, `0009` apenas deriva `periodicidade`/`data_inicio`/`primeiro_vencimento`, `0010` Campos not-null + regra de valor; `0011` metadados de choices.
- `prepare_subscription_migration` com `--report`/`--resolve`/`--deactivate`/`--check`: report somente leitura, mutações bloqueiam linha e auditam, `--check` falha enquanto houver linha sem resolver, sem desativação em massa.
- `licencas/services/assinaturas.py`: `atualizar_comercial`, `ativar_assinatura` (rejeita valor zero), `bloquear_assinatura`, `desbloquear_assinatura` e `desativar_assinatura`, todos com lock de linha, `full_clean()` e `EventoAuditoria` na mesma transação.
- Desvio registrado: variantes de migração raw com linhas `valor=None` são inviáveis após o schema final nos bancos (vazios) — o staging nunca grava `ativo`; invariantes cobertos por testes de serviço/comando, e `--check`/`--report` contam como pendência qualquer linha com `valor_recorrente=0`.
- **Autoritativo validado**: `migrate` OK; `audit_legacy_data` → `invalid_documents=0`, `duplicate_documents=0`, `duplicate_client_system_pairs=0`; `prepare_subscription_migration --check` → OK.
- Suíte completa → **66 passed**; `manage.py check` → nenhum issue.

### Task 4 - CRUD de clientes e sistemas no portal

- Selectors (`listar_clientes`, `listar_sistemas`) com filtros `q`, `status` e paginação de 25; bug corrigido: busca com texto sem dígitos não pode gerar filtro `icontains=''` que casa com tudo.
- Services de domínio (`criar_cliente`, `atualizar_cliente`, `bloquear/desbloquear_cliente`, `criar_sistema`, `atualizar_sistema`) com row lock, `full_clean()` e `EventoAuditoria`; bug corrigido: update aplicava `cleaned_data` explicitamente sobre a linha travada (trocar `form.instance` não reaplica dados limpos).
- Forms com Duralux; `Sistema.codigo` imutável no update (service força o código original).
- Templates de lista/form/detail para clientes e sistemas; `--check` de migrações detecta o drift por metadados.
- Testes cobrem: redirect anônimo, readonly do Consulta (403), Cadastro mutante, formulário re-renderizado com documento inválido, filtros por nome/status, detalhes, paginação 25 e Código imutável.
- Suíte → **76 passed**; `manage.py check` sem issues.

### Task 5 - Workflow de assinaturas no portal

- `AssinaturaForm` com seleção de cliente/sistema, valor, periodicidade, diário/vencimento e caridade; par duplicado rejeitado na validação de formulário ("já existe").
- Views: lista com filtros (cliente/sistema/periodicidade/status), create/update por service, e ações de estado POST-only (`HTTP 405` para GET) — `ativar`, `bloquear` (motivo obrigatório; sem motivo re-renderiza confirmação), `desbloquear`, `desativar`; Consulta fica em leitura (403).
- Sugestão de `primeiro_vencimento` permanece provisória até o `ConfiguracaoFinanceira` do Plano 04 assumir o padrão.
- Templates de assinaturas (list/form/detail/confirm) e link na sidebar.
- **Gate C fechado**: CRUD e assinatura funcionando sem Admin; suíte completa → **83 passed**; `manage.py check` → nenhum issue; migrations do plano aplicadas também no autoritativo com auditoria e `--check` zerados.

## Execução do Plano 04

### Task 1 - Modelos financeiros e constraints

- App `financeiro` criado: `ConfiguracaoFinanceira` (singleton com pk forçado a 1 por modelo + `CheckConstraint(Q(pk=1))`; ORM não garante segunda linha ao nível do banco), `Cobranca` (competência única por assinatura, valor positivo, carência após vencimento, origem, campos de cancelamento e timestamps para ETag/updated_since) e `Pagamento` (origens manual/gateway/legacy, statuses confirmed/reversed, ator/confirmação/estorno e timestamps).
- Registrações no AdminSite superusuário.
- Vermelho (tabelas ausentes) → verde: `test_models.py` → **7 passed**.

### Task 2 - Cronograma e gerador idempotente de cobranças

- `meses_por_periodicidade` + `gerar_cobrancas_assinatura` com `relativedelta`, `get_or_create` idempotente, `IntegrityError` capturado para corrida concorrente (retorna linha existente), snapshot de carência (assinatura sobrepõe `ConfiguracaoFinanceira`).
- Casos cobertos: ciclos por periodicidade, término fixo, indefinido mantém próxima, carência com override e global, inativo não gera, chamadas repetidas sem duplicidade.
- Comando `gerar_cobrancas` com contadores determinísticos (`subscriptions_scanned`, `charges_created`, `charges_existing`, `subscriptions_failed`), `--today` opcional em produção, falha por assinatura sem abortar as demais e exit não-zero com falhas.
- Suíte financeiro → **21 passed**.

### Task 3 - Posição financeira, pagamentos, estornos e cancelamento

- `FinancialPosition` imutável com `code/allowed/oldest_due_date/grace_ends_on/outstanding_amount`; derivada, nunca persistida.
- Fronteira exata: vencimento → CURRENT; dentro da carência → OVERDUE_IN_GRACE; após fim da carência → DELINQUENT; carência zero vai direto a DELINQUENT.
- Estornos: apenas pagamentos `confirmed` somam ao saldo; `reversed` contribui zero — regressão prova que a posição retorna exatamente ao valor pré-pagamento; duplicidade e motivo em branco rejeitados.
- `cancelar_cobranca_scl` atômico: origem scl obrigatória, sem pagamento confirmado, motivo obrigatório, ator/tempo registrados e canceladas nunca afetam a licença.
- Pagamento acima do saldo rejeitado; parcial mantém aberto; pagamento total marca `PAGA`.
- **Plano 04 Tasks 1-3 concluídas**: suíte completa → **112 passed**; `manage.py check` sem issues.

### Task 4 - Contas de gateway e emissões seguras

- `cryptography>=45,<47` no Windows Python e `requirements.txt`; `SCL_CONFIG_ENCRYPTION_KEYS` em settings/`.env.example`.
- `financeiro/crypto.py` com `MultiFernet` (novas primeiro), JSON canônico, `encrypt_config`/`decrypt_config`.
- Modelos: `ContaGateway` (múltiplos por provedor; boleto/PIX; conexão com status; auditoria_users), `EmissaoCobranca` (chave idempotente, status transitions, `pending_unknown` guardas do plan 07; uma emissão ativa por cobrança via partial unique; `(conta, id_externo)` único quando presente), `EventoGateway` (dedup em `(provedor, id_evento_externo)`) e `Pagamento` com proveniência de gateway obrigatória (`emissao_gateway`, `provedor_gateway` + uniqueness por provedor+id externo apenas para origem gateway).
- `salvar_credenciais` criptografa, valida chaves por provedor e audita sem nunca gravar valores/segredos no JSON da auditoria.
- Ajustes registrados: testes com `IntegrityError` precisam de savepoint (`transaction.atomic`) dentro de testes `django_db`; camadas escritas por processamento corrigidas antes do primeiro green.
- Suíte financeiro → **38 passed**.

### Task 5 - Portal financeiro

- Rotas: cobrancas list/detail (com ledger e ações), `pagamento-registrar`, `pagamento-estornar` (POST-only), `cobranca-cancelar` (GET confirmação 200 + POST executada e auditada), configuração (Admin com audit) e pagamentos list.
- Papéis: Financeiro/Administrador mutam; Consulta/Cadastro leem (403 em POST); CSRF testado com client reforçado.
- Duralux templates para cobranças/pagamentos/configuração com badges e filtros por status/vencimento; `cancel.html` com alerta de ação auditada.
- Deviation registrada: confirmações de estorno/cancelamento renderizam via GET; a execução é POST-only com CSRF (objetivo de proteção idêntico ao wording original do plano).
- Correções menores anotadas: datas localizadas (pt-br render) em vez de ISO nas asserções do portal; `pago_em` explicito nos POSTs de pagamento.
- **Plano 04 concluído**: suíte completa → **129 passed, 1 warning** (naive datetime em dado de teste de proveniência); `manage.py check` sem issues.
- Autoritativo: migrations financeiro aplicadas; `gerar_cobrancas --today 2026-09-20` → `0/0/0/0` deterministicamente.

## Execução do Plano 05

### Task 1 - OAuth2 para integrações legadas

- `django-oauth-toolkit>=3.0,<4` e `djangorestframework>=3.16,<3.17` instalados e declarados.
- App `integracoes` com `IntegracaoLegado` (campos exatos do plano; 1-1 com `Application`; `limite_requisicoes` definido como req/min 1-10000; `redes_permitidas` CIDRs; `credencial_expira_em`; `ultimo_uso_em`).
- `/api/v1/integrations/token/` via `IntegrationTokenView` com gates: inativa (403), expirada (403), origem fora dos CIDRs (403), escopo fora da lista da integração (403) e segredo inválido (401 do DOT); `ultimo_uso_em` atualiza somente no sucesso (regressão do caso de falha).
- Configurações OAUTH2_PROVIDER (15min, escopos) e modelos DOT explícitos em settings — descoberta: o autodetector de migrações exigiu `OAUTH2_PROVIDER_APPLICATION_MODEL` como setting Django.
- Vermelho (app/rota ausente + bug de nome em `_origem_confere` corrigido) → verde: **7 passed**.
- Suíte completa → **136 passed, 1 warning**; `manage.py check` sem issues.

### Task 2 - Policies, referências externas e origem de cobrança

- Modelos em `integracoes`: `PoliticaIntegracao` (AuthorityMode: scl/legacy/shared com campos de leitura/escrita; única por integração+recurso), quatro referências externas concretas sobre base abstrata (unique por integração+external_id, marca `proprietaria` com unique condicional; integration é PROTECT), `AssinaturaOrigemCobranca` (1-1) e `RequisicaoIntegracao` (idempotência, estado, hash, contador, IP e erro).
- Exceções de domínio `IntegrationPermissionDenied` e `IntegrationConflict`.
- `authorize_fields` aplica a matriz por recurso/oper; `campos_sob_authoridade(_legado)` para guard no portal.
- `rejeitar_campos_protegidos` em licencas/services/clientes (Cliente e Sistema), assinaturas e financeiro; Sistema mapeado como sem recurso (sem restrição), Cliente/Cobrança/Pagamento/Assinatura auditados.
- `obter_ou_criar_referencia` idempotente; `transferir_propriedade_referencia` bloqueia requisições em andamento, exige motivo e audita.
- `trocar_origem_cobranca` bloqueia transações em andamento, exige motivo, audita em transação, e o gerador interno (`_origem_externa`) agora ignora assinaturas sob origem legada.
- Fixtures organizadas: `cliente_payload` movida ao conftest da raiz do projeto (conftest é por diretório — todas as apps compartilham); bugs de kwarg/guard corrigidos no caminho (troca de origem usava kwarg errado; Sistema sem recurso mapeado poderia barrar update de sistemas).
- Suíte completa → **152 passed, 1 warning**.

### Task 3 - Infraestrutura compartilhada da API

- `JanelaRateLimit` + `consume_rate_limit` em PostgreSQL com row lock/upsert; buckets únicos e delete oportunista; hash de chaves corrigido para UUID via `str(value)`.
- `integrações/api`: `EnvelopeError` única em `exceptions.py` (bug duplicado resolvido), envelope `{code, message[, details]}` catch em `IntegrationAPIView` (base própria com pipeline: rate por origem→auth→CIDR→rate por integração), autenticação Bearer→AccessToken→integration (401 genérico), `permissions.exigir_escopo`, `etag.version_for`/`check_if_match`, `idempotency.idempotent_mutation` (replay 200/estado, 409 conflito de hash, 409 em processamento) e `throttles` com parsing de `300/min` + trusted proxies.
- Rotas montadas em namespace `integrations` com `/echo/` adaptador para URLs Django (descoberta: `IntegrationAPIView` não é View; adaptador function-based resolve).
- Descobertas registradas: settings `OAUTH2_PROVIDER_*_MODEL` exigidas pelo autodetector; fixture `integration_factory` tornada única por chamada (nome unique).
- Suíte completa → **157 passed, 1 warning**; `manage.py check` sem issues.

### Task 4 - Endpoints de clientes/assinaturas

- `serializers_clientes`/`serializers_assinaturas` com campos explícitos (sem `__all__`), `external_id`, `internal_id`, `version` (SHA-256 determinístico) e `updated_at` ISO.
- Endpoints `/clients/`, `/clients/<external_id>/`, `/clients/batch/` e `/subscriptions/` via integrações API base:
  - GET com cursor, filtros por `external_id`/documento/estado/`updated_since`, registros inativos visíveis.
  - POST cria com referência externa na MESMA transação; idempotência com replay; SCL_MASTER `403`, documento único (409); PATCH compartilhado exige If-Match (409 em ausente/obsoleto); batch com 1 válido/1 inválido.
- Descobertas e ajustes: escopo via `allow_scopes` (DOT); serialização JSON-friendly (datas ISO; rate bucket em datetime UTC seguro); PATCH exige `Idempotency-Key` pelo pipeline (mesma regra de mutação idempotente); carga com IntegrityError/ValidationError mapeados a 409; views rearranjadas para eliminar circular import; fixtures alinhadas.
- Suíte → **35 passed**; completa → **164 passed, 1 warning**; check sem issues.

### Task 5 - Cobrança/pagamento/estorno legados

- Proveniência `Pagamento.integracao` (PROTECT) com constraint única `(integracao, identificador_externo)` para origem legacy e exigência de integração em tal origem; `serializers_financeiro` com versão e updated_at.
- `integracoes/services/financeiro.py`: `criar_cobranca_legado` (somente assinatura com origem legada; competência única; origem=`legacy`; referência externa na MESMA transação), `registrar_pagamento_legado` (lock, saldo, proveniência, referência, status, auditoria), `estornar_pagamento_legado` (proprietário obrigatório) e `cancelar_cobranca_legado` (bloqueia paga; motivo obrigatório).
- Endpoints: `/charges/` create+list, `/charges/<external_id>/` detalhe+PATCH cancelar, `/payments/`, `/payments/<external_id>/reverse/` com Idempotency-Key, escopos e envelope.
- Testes cobrem external_id única (409), estado imediato da posição financeira por participação de cliente/assinatura/cobrança/pagamento/estorno legados (posicao_antes=100; depois=0; após estorno volta a 100).
- Desvios registrados: testes de estorno exigem `Idempotency-Key` (produção idêntica); external_id e não identificador_externo alimenta referência.
- Suíte módulo → **2 passed**; completa → **166 passed, 1 warning**; `check` sem issues.

### Task 6 - Portal administrativo de integrações e Gate E

- `integracoes/views.py` com `list/detail/create/rotate/revoke` restritos a Administrador/superusuário (login_required fora do guard para redirect correto de anônimo).
- Sessão one-time armazenando o segredo na criação/rotação apenas uma vez na página `rotate_secret.html`; chamadas subsequentes geram e mudam o Application secret; tokens expiram.
- CSRF em mutações; auditoria com eventos `integracao.criada`, `.credencial.rotacionada`, `.revogada`; Consulta não pode mutar (403).
- Templates de list/form/detail com badges e rotação segura.
- **Gate E fechado**: suíte completa → **170 passed, 1 warning**; `manage.py check` sem issues.

## Execução do Plano 07

### Task 1 - Protocolo, contrato e FakeAdapter

- `financeiro/gateways/base.py` com `GatewayAdapter` Protocol e dataclasses `GatewayAccountConfig`, `IssueCommand`, `IssueResult` (external_id, status, method, digitable_line, pix_copy_paste, pix_qr_text, presentation_url, hybrid), `QueryResult`, `CancelResult`, `WebhookEvent`.
- `GatewaysTemporaryError`/`GatewayAuthenticationError`/`GatewayValidationError` como exceções de base.
- `FakeAdapter` com armazenamento de classe compartilhado entre instâncias (descoberta: `get_adapter` cria novas instâncias e o estado precisa ser durable para cancelamentos e consultas funcionarem).
- `registry.register_adapter` (provedores efi/sicredi/sicoob/fake) e `get_adapter(account)`; duplicação de provedor verificada com ajuste de escopo de registro entre testes.
- `assert_gateway_contract` cobre emitir/consultar/cancelar; testes cobrem timeout mapeado a `GatewayTemporaryError`, credenciais inválidas, meio não-suportado e url `allowed_hosts`.
- Suíte financeiro → **55 passed**.

### Task 2 — Serviço transacional de emissão/cancelamento

- `financeiro/services/emissoes.py`:
  - Duas fases: `REQUESTED` no banco e chamada do adaptador fora do lock; estado normalizado com `pending_unknown` quando o timeout é ambiguo e exige query ao provedor antes de retry/reissue.
  - `emitir_cobranca`: apenas cobrança ABERTA; conta ativa; meio habilitado; apenas uma emissão ativa (REQUESTED/ISSUED) por cobrança.
  - `cancelar_emissao` com idempotência; provider devolvendo unknown levanta erro que NÃO marca `CANCELLED` local.
  - Auditoria `emissao.cobranca.emitida` e `...cancelada` nas transações.
- **Suíte completa → 179 passed, 1 warning**.

### Task 3 — Webhook routing e pagamento idêntico

- `financeiro/api/{webhooks.py, urls.py}` montados em `/api/v1/payments/webhooks/<provedor>/<conta>/`:
  - Conta ausente → 404, inválido → 401; parse raw via `adapter.parse_webhook` antes de qualquer parser interno.
  - `financeiro/services/webhooks.py` roteia com dedupe em `(provedor, id_evento_externo)` via `get_or_create` com `IntegrityError`; evento repetido devolve duplicado.
- Pagamento de gateway com proveniência completa (`emissao_gateway`, `provedor_gateway`, `identificador_externo`); errados/out-of-order não criam pagamento duplicado.
- Descobertas registradas: fluxo de desvio por estado compartilhado de classe; fake factory de timeout não deve vazar entre testes;_ordem de setup de fixtures function.
- Suíte completa → **180 passed, 1 warning**; `manage.py check` sem issues.

### Task 4 — Portal de emissões

- Rotas: `cobrancas/<pk>/emissoes/nova/` (POST com conta+meio), `emissoes/<pk>/` detalhar e `emissoes/<pk>/cancelar` (POST+CSRF e motivo opcional).
- Suíte módulo → **2 passed**; completa → **182 passed, 1 warning**; `check` sem issues.

### Task 5 — Spec técnica dos provedores

- Specs não-confidenciais em `_reversa_sdd/specs/gateways/`: `efi.md`, `sicredi.md`, `sicoob.md` e `contract-matrix.md` com requisitos por provedor e definições de estado/assinatura/idempotência.
- Implementação de código dos adaptadores fica bloqueada até documentação oficial + credenciais de homologação (o operador confirmando).

### Plano 07 concluído — suíte financeiro 58 passed; completa 182 passed, 1 warning.

## Execução do Plano 08

### Tasks 1-3

- `app/logging.py` com `RedactingFilter` (token/client_secret/authorization/senha/password/secret/document/cpf/cnpj → `[REDACTED]`); testes de redação → **7 passed**.
- Verificações de produção: `SECURE_PROXY_SSL_HEADER`, cookies httpOnly e SameSite Lax/Strict, `SECURE_REFERRER_POLICY`, nosniff, DEBUG falsificado. Teste de segurança → **1 passed**.
- Locust: `tests/load/license_api.py` e `tests/load/integration_api.py` com posts/upserts conforme os endpoints existentes; diretrizes executáveis (100u licença e 25u integração, p95 e error-rate) já documentadas para serem aplicadas em staging quando o ambiente estiver disponível.

### Task 5 - Runbooks

- `backup-restore.md`, `deploy.md` (migração via job, collectstatic, Gunicorn, health, scheduler 00:15 America/São_Paulo com lock distribuído), `rollback.md` (classificação reversível/required-restore, rollback de imagem, feature disabled, pausa de webhooks, preservação do kid), `portal-rollout.md` (cohortes).

### Plano 08 concluído (parte executável aqui)

- Suíte final: **191 passed, 1 warning** no banco descartável; `manage.py check` sem issues.

## Restante voluntariamente bloqueado (limitação de ambiente/homologação)

- Adaptadores oficiais Efí/Sicredi/Sicoob — exigem documentação oficial e credencial de homologação pelo operador.
- Deploy com Docker/PostgreSQL-real — exigem Docker Desktop e credenciais fornecidas na hora, com runbooks prontos.
- Testes de carga reais exigem staging ativo com Locust; a base de cenários está pronta.
