# SCL: design de licenciamento e controle financeiro

**Data:** 2026-09-20  
**Status:** aprovado pelo usuário e pronto para execução planejada  
**Projeto:** Sistema de Controle de Licenças (SCL)

## 1. Contexto

O SCL controla quais sistemas cada empresa cliente pode usar e a situação financeira de cada vínculo cliente-sistema. Embora existam projetos de referência com nomes semelhantes, o SCL possui domínio próprio e não deve copiar regras de negócio do `controlelicenca`.

O sistema atual é um projeto Django pequeno, operado pelo Django Admin. Ele possui os modelos `Cliente`, `Sistema`, `ClienteSistema` e `AcessoMaquina`, mas ainda não possui portal próprio, financeiro, API de validação ou suíte de testes.

O novo produto deve oferecer:

- cadastro de clientes e sistemas;
- assinatura comercial por cliente-sistema;
- cobranças mensais, trimestrais, semestrais e anuais;
- pagamentos manuais e automáticos via Efí, Sicredi e Sicoob;
- vencimento, carência e bloqueio por inadimplência;
- bloqueio global do cliente e bloqueio específico por sistema;
- API REST para validação diária da licença;
- API administrativa para sistemas legados consultarem e alimentarem clientes, assinaturas, cobranças e pagamentos;
- token assinado para contingência durante indisponibilidade temporária;
- portal interno baseado no design system Duralux já disponível.

## 2. Objetivos

1. Centralizar o cadastro dos clientes e dos sistemas contratados.
2. Manter histórico financeiro confiável por assinatura.
3. Aplicar uma única regra de decisão de licença em portal e API.
4. Permitir aviso durante a carência e bloqueio após seu término.
5. Funcionar de forma segura durante indisponibilidade temporária do SCL.
6. Integrar Efí, Sicredi e Sicoob sem acoplar o domínio a um fornecedor específico.
7. Permitir integração controlada com sistemas legados sem duplicar cobranças ou perder alterações.
8. Migrar gradualmente a operação do Django Admin para um portal interno.

## 3. Fora do escopo funcional

- portal de autoatendimento para empresas clientes;
- emissão fiscal;
- contabilidade completa, fluxo de caixa ou plano de contas;
- múltiplas moedas;
- crédito financeiro ou compensação automática de pagamento excedente;
- arquitetura de microsserviços;
- aplicação SPA em React;
- provedores financeiros diferentes de Efí, Sicredi e Sicoob;
- sincronização iniciada pelo SCL contra APIs legadas;
- webhooks de saída do SCL para sistemas legados;
- bloqueio em tempo real depois que um token diário válido já foi emitido.

## 4. Decisões aprovadas

| Tema | Decisão |
|---|---|
| Arquitetura | Monólito modular Django |
| Interface | Portal server-rendered com Django Templates e JavaScript progressivo |
| Referência visual | `C:\Users\leand\projetos\lotesis` |
| Unidade de cobrança | Um vínculo/assinatura por cliente-sistema |
| Periodicidades | Mensal, trimestral, semestral e anual |
| Vigência | Prazo determinado ou indeterminado |
| Vencimento | Dia fixo do mês |
| Configuração | Padrão global com exceção por cliente-sistema |
| Inadimplência | Avisar durante a carência e bloquear depois dela |
| Bloqueio | Global por cliente e específico por cliente-sistema |
| Pagamento | Manual e automático |
| Gateways | Cadastro multi-conta para Efí, Sicredi e Sicoob |
| Seleção do gateway | Escolha manual por cobrança antes da emissão externa |
| Meios de cobrança | Boleto e PIX, conforme habilitação da conta |
| Usuários do portal | Equipe interna |
| Validação | Consulta no primeiro acesso de cada dia |
| Identificação da API | Código do sistema e credencial própria, além do CNPJ/CPF |
| Contingência | Aceitar token diário ainda válido quando o SCL estiver indisponível |
| Contrassenha | Token assinado assimetricamente; MD5 não será usado |
| API administrativa | Legado consulta e envia clientes, assinaturas, cobranças e pagamentos |
| Comunicação com legado | Sempre iniciada pelo sistema legado; sem polling ou webhook de saída pelo SCL |
| Autoridade dos dados | Configurável por integração e por recurso |
| Conflitos compartilhados | Controle otimista por versão/ETag; conflito retorna HTTP 409 |
| Geração de cobranças | Uma única origem por assinatura: SCL ou uma integração |
| Pagamento legado | Integração registra e estorna somente pagamentos criados por ela |
| Carga inicial | Upsert em lotes controlados de até 100 itens |

## 5. Arquitetura

O SCL continuará como uma única aplicação Django implantável, com limites internos explícitos.

```text
Portal interno ──────────────────────┐
API REST de licenciamento ──────────┼── Serviços de domínio ── PostgreSQL
API administrativa para legados ───┘           │
                                                ├── Agendador diário
                                                └── Adaptadores financeiros
                                                          │
                                             Efí / Sicredi / Sicoob
```

### 5.1 Módulos

**Cadastros**

Responsável por clientes, sistemas, documentos e credenciais de integração.

**Assinaturas**

Responsável pelo vínculo cliente-sistema, preço, periodicidade, vigência, configurações excepcionais e bloqueios específicos.

**Financeiro**

Responsável por cobranças, contas de gateway, emissões externas, pagamentos, estornos, inadimplência, conciliação e eventos de integração.

**Licenciamento**

Responsável pela decisão de acesso, API REST, emissão de token diário e auditoria das consultas.

**Integrações administrativas**

Responsável pelas credenciais dos sistemas legados, políticas de autoridade, referências externas, idempotência, consultas e cargas em lote.

**Portal**

Responsável por autenticação humana, navegação, formulários e apresentação. Não contém regras de decisão financeira ou de licença.

### 5.2 Organização inicial do código

O app existente `licencas` continuará responsável por `Cliente`, `Sistema` e `ClienteSistema`. Serão adicionados módulos ou apps próprios para financeiro, licenciamento e integrações administrativas. Tabelas existentes não serão movidas antes de verificar os dados reais.

Views do portal e endpoints da API chamarão os mesmos serviços de domínio. Nenhuma regra de acesso poderá existir apenas no template, na view ou no `admin.py`.

## 6. Modelo de dados

### 6.1 Cliente

Campos essenciais:

- identificador interno;
- CNPJ/CPF normalizado, validado e único;
- razão social ou nome;
- nome fantasia opcional;
- contatos e endereço;
- `ativo`;
- `bloqueado`;
- motivo do bloqueio;
- data do bloqueio;
- timestamps de criação e alteração.

`ativo=false` representa cadastro fora de operação. `bloqueado=true` representa interrupção explícita e reversível. Qualquer uma das condições impede acesso a todos os sistemas do cliente.

### 6.2 Sistema

Campos essenciais:

- identificador interno;
- código público único e imutável;
- nome;
- descrição opcional;
- `ativo`;
- timestamps.

Um sistema inativo não autoriza nenhum cliente.

### 6.3 CredencialSistema

Campos essenciais:

- sistema;
- identificador público da credencial;
- hash do segredo;
- `ativo`;
- data de criação;
- data de expiração opcional;
- último uso;
- data de revogação.

O segredo será mostrado somente no momento da criação. O banco não armazenará o segredo original. Será possível manter duas credenciais válidas temporariamente para rotação sem interrupção.

### 6.4 ClienteSistema

O modelo existente evoluirá para representar a assinatura comercial.

Campos essenciais:

- cliente;
- sistema;
- valor recorrente;
- periodicidade: mensal, trimestral, semestral ou anual;
- data de início;
- data final opcional;
- primeiro vencimento;
- `ativo`;
- `bloqueado`;
- motivo e data do bloqueio;
- dia de vencimento opcional;
- dias de carência opcionais;
- origem geradora das cobranças: SCL ou uma integração legada específica;
- timestamps.

Dia de vencimento e carência nulos usam a configuração global. O dia aceito ficará entre 1 e 28 para evitar datas inexistentes em meses curtos.

O par cliente-sistema será único. Encerramento e eventual reativação reutilizam o mesmo vínculo, enquanto cobranças e auditoria preservam o histórico. A restrição será criada somente após verificar e tratar eventuais duplicidades no banco atual.

### 6.5 ConfiguracaoFinanceira

Configuração global única:

- dia padrão de vencimento, entre 1 e 28;
- dias padrão de carência, maior ou igual a zero;
- timezone operacional;
- timestamps;
- usuário responsável pela última alteração.

A configuração inicial recomendada é dia 5, mantendo a quantidade de dias de carência como dado configurável.

### 6.6 Cobranca

Campos essenciais:

- assinatura cliente-sistema;
- competência ou identificador do ciclo;
- data de vencimento;
- fim da carência aplicado;
- valor original;
- estado base: aberta, parcialmente paga, paga ou cancelada;
- descrição;
- origem: SCL ou integração legada;
- timestamps.

A combinação assinatura + ciclo será única. O fim da carência será gravado na geração como fotografia da regra vigente, impedindo que uma mudança global altere retroativamente uma cobrança já emitida. A condição “vencida” não será persistida como fonte de verdade: será calculada pelo saldo remanescente e pela data atual.

### 6.7 Pagamento

Campos essenciais:

- cobrança;
- valor;
- data e hora do pagamento;
- forma de pagamento;
- origem: manual, gateway ou integração legada;
- emissão externa relacionada, quando automática;
- integração legada relacionada, quando aplicável;
- identificador externo opcional e único por provedor;
- usuário responsável quando manual;
- estado confirmado ou estornado;
- motivo do estorno;
- timestamps.

Uma cobrança pode receber vários pagamentos. Pagamento parcial não quita a dívida. Pagamento acima do saldo não será aceito na primeira versão.

### 6.8 ContaGateway

Cada registro representa uma conta ou convênio utilizável para emissão financeira. O mesmo provedor poderá possuir várias contas.

Campos essenciais:

- identificador público;
- nome interno;
- provedor: Efí, Sicredi ou Sicoob;
- ambiente: homologação ou produção;
- `ativo`;
- boleto habilitado;
- PIX habilitado;
- configuração pública do convênio;
- credenciais criptografadas;
- certificado e chave privada protegidos, quando exigidos;
- segredo ou configuração de webhook;
- data do último teste de conexão;
- resultado do último teste;
- timestamps;
- usuário responsável pela criação e última alteração.

A chave de criptografia dos segredos ficará fora do banco, em variável de ambiente ou secret store. O portal mostrará segredos apenas no momento da inclusão ou substituição. Cada adaptador validará os campos específicos do seu provedor.

### 6.9 EmissaoCobranca

Representa cada tentativa de emitir uma cobrança interna em um gateway.

Campos essenciais:

- cobrança interna;
- conta de gateway;
- meio: boleto ou PIX;
- chave idempotente da solicitação;
- identificador externo;
- estado: solicitada, emitida, falhou, cancelada, paga ou expirada;
- data e hora da solicitação e emissão;
- vencimento externo;
- linha digitável e URL do boleto, quando aplicável;
- código PIX copia e cola, QR Code ou URL, quando aplicável;
- erro normalizado e detalhe técnico protegido;
- timestamps.

Uma cobrança pode possuir várias tentativas históricas, mas apenas uma emissão externa ativa. Para trocar de gateway, a emissão anterior deve ser cancelada ou comprovadamente invalidada antes da nova solicitação.

### 6.10 EventoGateway

Campos essenciais:

- provedor;
- identificador externo único;
- tipo do evento;
- hash ou conteúdo protegido do payload;
- data de recebimento;
- estado de processamento;
- quantidade de tentativas;
- erro mais recente;
- data de conclusão.

Esse registro garante idempotência e auditoria de webhooks repetidos dos gateways financeiros.

### 6.11 ConsultaLicenca

Campos essenciais:

- `request_id`;
- credencial e sistema;
- cliente encontrado, quando existir;
- assinatura encontrada, quando existir;
- documento mascarado ou hash pesquisável;
- versão do aplicativo consumidor;
- identificador de instalação opcional;
- IP de origem;
- data e hora;
- código da decisão;
- acesso permitido;
- latência.

Credenciais e tokens completos nunca serão registrados.

### 6.12 TokenLicenca

Campos essenciais:

- identificador único `jti`;
- cliente;
- sistema;
- assinatura;
- hash do token;
- identificador da chave de assinatura `kid`;
- data e hora de emissão;
- data e hora de expiração;
- data de revogação opcional;
- código da decisão que permitiu a emissão.

O token completo será entregue ao consumidor, mas o SCL armazenará apenas metadados e hash.

### 6.13 IntegracaoLegado

Representa um sistema legado autorizado a consultar ou alimentar o SCL.

Campos essenciais:

- identificador público;
- nome;
- `client_id` único;
- hash do `client_secret`;
- `ativo`;
- escopos autorizados;
- limite de requisições;
- redes de origem permitidas, quando configuradas;
- data de expiração da credencial;
- último uso;
- timestamps;
- usuário responsável pela criação, rotação e revogação.

A credencial administrativa é independente da credencial usada pela API de licenciamento. O segredo será exibido somente na criação ou rotação.

### 6.14 PoliticaIntegracao

Define a autoridade de uma integração para cada recurso: cliente, assinatura, cobrança e pagamento.

Modos:

- `SCL_MASTER`: a integração consulta, mas não altera o recurso;
- `LEGACY_MASTER`: a integração altera, e os campos sob sua autoridade ficam protegidos no portal;
- `SHARED`: integração e portal alteram usando controle otimista de concorrência.

Campos essenciais:

- integração legada;
- tipo de recurso;
- modo de autoridade;
- campos permitidos para leitura;
- campos permitidos para escrita;
- timestamps.

Uma política nunca autoriza operações além dos escopos da credencial.

### 6.15 ReferenciasExternas

Serão usadas relações concretas para preservar integridade referencial:

- `ClienteReferenciaExterna`;
- `AssinaturaReferenciaExterna`;
- `CobrancaReferenciaExterna`;
- `PagamentoReferenciaExterna`.

Cada relação contém integração, identificador externo, objeto interno, indicação de propriedade, versão externa opcional e timestamps. A combinação integração + identificador externo será única dentro de cada tipo de recurso.

Um objeto interno pode ter várias referências externas, mas no máximo uma integração proprietária. Em modo `LEGACY_MASTER`, somente a proprietária pode alterar o registro; as demais referências ficam limitadas à leitura. Em modo `SHARED`, integrações autorizadas podem escrever usando controle de versão.

CNPJ/CPF, nomes, competência ou valores não serão usados como chave idempotente. Eles podem ajudar na validação, mas a identidade externa depende do `external_id`.

### 6.16 RequisicaoIntegracao

Registra a operação administrativa para idempotência e auditoria.

Campos essenciais:

- integração legada;
- identificador da requisição;
- chave de idempotência;
- método e endpoint;
- hash do payload;
- quantidade de itens recebidos, aceitos e rejeitados;
- código HTTP final;
- data de início e conclusão;
- erro normalizado;
- IP e metadados técnicos.

Payloads completos com dados pessoais ou financeiros não serão registrados indiscriminadamente. Erros por item poderão ser devolvidos na resposta e armazenados de forma protegida quando necessário para suporte.

## 7. Regras financeiras

### 7.1 Primeiro vencimento

O primeiro vencimento será persistido na assinatura para eliminar ambiguidades.

Ao sugerir essa data no portal:

1. Usa-se o dia de vencimento específico da assinatura ou o padrão global.
2. Se a data inicial ocorrer antes ou no dia configurado, sugere-se esse dia no mesmo mês.
3. Se a data inicial ocorrer depois do dia configurado, sugere-se o dia configurado do mês seguinte.
4. O usuário autorizado pode ajustar a primeira data antes de ativar a assinatura.

### 7.2 Vencimentos seguintes

Cada vencimento é calculado a partir do primeiro:

- mensal: acrescenta 1 mês;
- trimestral: acrescenta 3 meses;
- semestral: acrescenta 6 meses;
- anual: acrescenta 12 meses.

Como o dia máximo permitido é 28, não haverá ajuste silencioso para o último dia do mês.

### 7.3 Geração de cobranças

- Assinatura com término definido gera o cronograma até sua data final.
- Assinatura sem término mantém pelo menos a próxima cobrança criada.
- Uma rotina diária idempotente cria cobranças ausentes.
- A rotina processa somente assinaturas cuja origem geradora seja o SCL.
- Assinaturas controladas por integração recebem cobranças exclusivamente pela API administrativa.
- A API de licenciamento nunca cria cobrança como efeito colateral.
- A restrição assinatura + ciclo impede duplicidade em execuções concorrentes.
- Falha em um vínculo não impede o processamento dos demais; o erro fica registrado e observável.
- Alterações de preço, vencimento ou carência valem para ciclos ainda não gerados; qualquer recálculo de cobrança existente exige ação explícita e auditada.

Inicialmente, a rotina será um management command executado por agendador. Celery só será introduzido quando houver volume ou tarefas assíncronas suficientes para justificar sua operação.

A troca da origem geradora de uma assinatura será uma operação administrativa auditada. Ela exigirá conferência das competências já existentes e não poderá criar duas cobranças para o mesmo ciclo.

### 7.4 Carência

Para cada cobrança com saldo:

```text
hoje <= vencimento                  => em dia
vencimento < hoje <= fim_carencia  => vencida, acesso permitido com aviso
hoje > fim_carencia                => inadimplente, acesso bloqueado
```

Na geração, `fim_carencia = vencimento + dias_de_carencia` e o resultado fica armazenado na cobrança.

Com carência zero, a cobrança bloqueia a partir do dia seguinte ao vencimento. Havendo várias cobranças abertas, a mais antiga determina a mensagem e o fim da carência aplicável.

### 7.5 Pagamentos

- Baixa manual exige perfil Financeiro ou Administrador.
- O saldo é a soma de pagamentos confirmados menos estornos.
- Pagamento parcial mantém a cobrança aberta.
- Quitação elimina imediatamente o bloqueio financeiro.
- Bloqueio manual, inatividade ou término da assinatura continuam prevalecendo.
- Encerrar uma assinatura interrompe novos ciclos, mas não apaga nem quita débitos existentes.
- Pagamento enviado por integração é aplicado imediatamente após validação e idempotência.
- Uma integração pode estornar apenas pagamentos cuja origem seja ela própria.
- Pagamentos manuais, de gateway ou de outra integração não podem ser alterados pela API legada.

### 7.6 Integração automática

O SCL gera primeiro a cobrança interna, sem provedor. Um usuário Financeiro ou Administrador escolhe uma `ContaGateway` ativa e o meio boleto ou PIX para solicitar a emissão externa.

O domínio exporá uma interface comum de provedor financeiro. Os adaptadores Efí, Sicredi e Sicoob deverão:

- validar a configuração exigida pelo provedor;
- testar conexão sem expor credenciais;
- emitir boleto e PIX quando habilitados no convênio;
- consultar, cancelar e atualizar a emissão externa;
- verificar assinatura do webhook;
- converter estados externos para estados internos;
- usar identificadores idempotentes;
- consultar o provedor quando o evento recebido não for suficiente ou confiável;
- registrar falhas sem aplicar baixa parcial inconsistente.

Webhooks serão roteados pela conta pública e pelo provedor, sem expor o identificador interno ou qualquer segredo. Um evento de pagamento confirmado cria uma baixa automática vinculada à emissão. Repetições do mesmo evento não criam pagamentos duplicados.

O primeiro release de produção exige os três adaptadores homologados. Uma conta pode habilitar somente boleto, somente PIX ou ambos, conforme o contrato bancário.

## 8. Decisão de licença

Um único serviço, por exemplo `LicenseDecisionService`, será a fonte de verdade.

Ordem obrigatória:

1. Validar formato da requisição.
2. Autenticar a credencial do sistema.
3. Confirmar que o código informado corresponde à credencial.
4. Confirmar que o sistema está ativo.
5. Normalizar e localizar o CNPJ/CPF.
6. Confirmar que o cliente está ativo.
7. Confirmar que o cliente não está bloqueado globalmente.
8. Localizar a assinatura cliente-sistema.
9. Confirmar vigência, situação ativa e ausência de bloqueio específico.
10. Calcular cobranças com saldo e sua carência.
11. Emitir a decisão e, quando permitido, o token diário.
12. Registrar a auditoria sem dados secretos.

Precedência dos impedimentos:

```text
autenticação da API
  > sistema inativo
  > cliente inexistente/inativo/bloqueado
  > assinatura inexistente/fora da vigência/inativa/bloqueada
  > inadimplência após carência
  > aviso de atraso dentro da carência
  > acesso em dia
```

## 9. API REST de licenciamento

### 9.1 Endpoint

```http
POST /api/v1/licenses/check
Authorization: Bearer <segredo-da-credencial>
Content-Type: application/json
```

Requisição:

```json
{
  "system_code": "SISTEMA_X",
  "document": "00000000000191",
  "installation_id": "workstation-01",
  "app_version": "1.4.0"
}
```

`installation_id` e `app_version` são campos de auditoria. Eles não criam, por si só, limitação de quantidade de máquinas nesta versão.

### 9.2 Resposta permitida e em dia

```json
{
  "allowed": true,
  "code": "ACTIVE",
  "message": "Licença ativa e pagamentos em dia.",
  "checked_at": "2026-09-20T11:00:00Z",
  "expires_at": "2026-09-21T03:00:00Z",
  "next_due_date": "2026-10-05",
  "grace_ends_on": null,
  "token": "<token-assinado>"
}
```

### 9.3 Resposta permitida com aviso

```json
{
  "allowed": true,
  "code": "OVERDUE_IN_GRACE",
  "message": "Existe uma cobrança vencida. Regularize até 2026-09-15 para evitar o bloqueio.",
  "checked_at": "2026-09-10T11:00:00Z",
  "expires_at": "2026-09-11T03:00:00Z",
  "oldest_overdue_date": "2026-09-05",
  "grace_ends_on": "2026-09-15",
  "token": "<token-assinado>"
}
```

### 9.4 Resposta bloqueada por inadimplência

```json
{
  "allowed": false,
  "code": "DELINQUENT",
  "message": "Acesso bloqueado por cobrança vencida após o período de carência.",
  "checked_at": "2026-09-16T11:00:00Z",
  "oldest_overdue_date": "2026-09-05",
  "grace_ends_on": "2026-09-15",
  "token": null
}
```

### 9.5 Códigos estáveis

- `ACTIVE`
- `OVERDUE_IN_GRACE`
- `CLIENT_NOT_FOUND`
- `CLIENT_INACTIVE`
- `CLIENT_BLOCKED`
- `SYSTEM_INACTIVE`
- `SUBSCRIPTION_NOT_FOUND`
- `SUBSCRIPTION_NOT_STARTED`
- `SUBSCRIPTION_EXPIRED`
- `SUBSCRIPTION_INACTIVE`
- `SUBSCRIPTION_BLOCKED`
- `DELINQUENT`

Os códigos são contrato de máquina e não devem ser alterados sem nova versão da API. As mensagens são humanas, localizáveis e não devem controlar lógica no consumidor.

### 9.6 Semântica HTTP

- `200`: decisão de negócio, permitida ou bloqueada;
- `400`: payload inválido;
- `401`: credencial ausente ou inválida;
- `403`: credencial válida sem autorização para o sistema informado;
- `429`: limite de chamadas excedido;
- `500/503`: falha interna ou dependência indisponível.

Cliente, assinatura ou inadimplência não usam HTTP 401/403 porque não são falhas de autenticação da chamada.

## 10. API administrativa de integração

Essa API é separada da validação de licença. Ela permite que sistemas legados autorizados consultem e alimentem clientes, assinaturas, cobranças e pagamentos.

O sistema legado sempre inicia a comunicação. O SCL não consulta APIs legadas periodicamente e não envia webhooks de saída nesta versão.

### 10.1 Autenticação e escopos

Será usado OAuth2 Client Credentials com access tokens curtos e sem refresh token. A integração troca `client_id` e `client_secret` por um token limitado aos escopos cadastrados.

Escopos iniciais:

- `clients:read` e `clients:write`;
- `subscriptions:read` e `subscriptions:write`;
- `finance:read` e `finance:write`;
- `payments:write` e `payments:reverse`.

Escopo, política de autoridade e campos permitidos serão verificados em conjunto. Possuir `finance:write`, por exemplo, não permite escrever cobranças quando a política desse recurso é `SCL_MASTER`.

### 10.2 Endpoints

```text
POST  /api/v1/integrations/token/

GET   /api/v1/integrations/clients/
POST  /api/v1/integrations/clients/
PATCH /api/v1/integrations/clients/<external_id>/
POST  /api/v1/integrations/clients/batch/

GET   /api/v1/integrations/subscriptions/
POST  /api/v1/integrations/subscriptions/
PATCH /api/v1/integrations/subscriptions/<external_id>/
POST  /api/v1/integrations/subscriptions/batch/

GET   /api/v1/integrations/charges/
POST  /api/v1/integrations/charges/
PATCH /api/v1/integrations/charges/<external_id>/
POST  /api/v1/integrations/charges/batch/

GET   /api/v1/integrations/payments/
POST  /api/v1/integrations/payments/
POST  /api/v1/integrations/payments/batch/
POST  /api/v1/integrations/payments/<external_id>/reverse/
```

Não haverá exclusão física por API. Cliente e assinatura serão inativados, cobrança será cancelada e pagamento será estornado por operações explícitas e auditáveis.

### 10.3 Identidade externa e idempotência

Todo item enviado conterá `external_id`, único dentro da integração e do tipo de recurso. O SCL devolverá também seu identificador interno e a versão atual do registro.

Criação de cobrança, pagamento e estorno exigirá `Idempotency-Key`. Repetir a mesma chave com o mesmo payload devolverá o resultado original. Repetir a chave com payload diferente retornará conflito `409`.

Pagamentos e cobranças não serão deduplicados por valor, data, documento ou competência sem uma referência externa explícita.

### 10.4 Autoridade e conflitos

Regras por recurso:

- `SCL_MASTER`: consultas permitidas conforme escopo; escrita externa retorna `403`;
- `LEGACY_MASTER`: escrita externa permitida; campos sob autoridade do legado ficam somente leitura no portal;
- `SHARED`: portal e legado escrevem; atualização exige `If-Match` com a versão recebida na leitura.

Em modo compartilhado, uma versão obsoleta retorna `409 VERSION_CONFLICT` com a versão atual, sem sobrescrever silenciosamente a alteração concorrente. A política “última gravação vence” não será usada.

Quando uma integração cria um registro em modo `LEGACY_MASTER`, sua referência se torna proprietária. Transferir propriedade exige ação administrativa explícita, auditada e sem requisições concorrentes em processamento.

### 10.5 Lotes controlados

Endpoints `batch` aceitarão no máximo 100 itens por requisição. Cada item terá resultado próprio e será processado em transação independente, de modo que um item inválido não reverta os demais.

O lote opera como upsert por `external_id`: cria quando a referência não existe e atualiza quando existe. Em modo `SHARED`, cada atualização do lote deve trazer a versão esperada. Os endpoints individuais mantêm semântica explícita: `POST` cria e retorna `409` se o `external_id` já existir; `PATCH` atualiza.

A resposta terá totais de recebidos, aceitos e rejeitados, além de código e mensagem por `external_id`. Envelope inválido retorna `400`; erros de um item válido estruturalmente aparecem no resultado desse item.

### 10.6 Consultas incrementais

Listagens serão paginadas por cursor e aceitarão filtros por:

- `external_id`;
- CNPJ/CPF normalizado, quando aplicável;
- estado;
- `updated_since`;
- assinatura, competência e vencimento, nos recursos financeiros.

Registros inativados, cancelados ou estornados continuam disponíveis para sincronização. Respostas incluem `updated_at` e versão.

### 10.7 Efeito no licenciamento

Clientes, assinaturas, cobranças, pagamentos e estornos recebidos pela API passam pelos mesmos serviços de domínio do portal. Depois do commit, a próxima consulta de licença utiliza imediatamente o novo estado financeiro.

Tokens de licença já emitidos permanecem válidos até a expiração diária aprovada; uma alteração administrativa não revoga retroativamente um token entregue ao consumidor.

Uma assinatura cuja origem de cobrança seja uma integração não será processada pelo gerador interno. Cobranças externas podem, posteriormente, ser emitidas por Efí, Sicredi ou Sicoob no portal, sem alterar sua origem contábil.

### 10.8 Semântica HTTP

- `200/201`: consulta ou mutação concluída;
- `400`: envelope ou payload estruturalmente inválido;
- `401`: token ausente ou inválido;
- `403`: escopo, política ou campo não autorizado;
- `404`: referência externa não encontrada;
- `409`: versão, idempotência ou identidade externa em conflito;
- `422`: regra de domínio rejeitou o item;
- `429`: limite da integração excedido;
- `500/503`: falha interna ou dependência indisponível.

## 11. Token de licença

### 11.1 Formato

Será utilizado token JWS/JWT assinado com RS256, escolhido por ampla compatibilidade entre linguagens. A chave privada permanece apenas no SCL. Sistemas consumidores recebem chaves públicas.

Claims mínimos:

- `iss`: identificador do SCL;
- `aud`: código do sistema consumidor;
- `sub`: identificador interno do cliente;
- `subscription_id`: assinatura autorizada;
- `decision`: `ACTIVE` ou `OVERDUE_IN_GRACE`;
- `iat`: emissão;
- `exp`: expiração;
- `jti`: identificador único;
- `kid`: informado no cabeçalho para rotação da chave.

O token não carregará valores de cobranças, endereços, contatos ou outros dados pessoais desnecessários.

### 11.2 Validade diária

O token expira no início do dia seguinte no timezone operacional `America/Sao_Paulo`, com timestamps transmitidos em UTC. O consumidor deve:

1. validar assinatura, emissor e audiência;
2. validar emissão e expiração;
3. aceitar apenas token destinado ao seu próprio código de sistema;
4. chamar a API quando não houver token válido para o dia atual;
5. negar acesso se o token expirou e a API não puder ser consultada.

Um pequeno desvio de relógio poderá ser tolerado somente na validação técnica. A tolerância não estenderá o token para outro dia operacional.

### 11.3 Consequência operacional

Um cliente que já recebeu token válido pode continuar acessando até a expiração diária mesmo que seja bloqueado depois da emissão. Essa latência máxima foi aceita como trade-off da contingência offline.

## 12. Portal interno

O portal usará a estrutura visual do Duralux disponível no SCL e os padrões de template do LoteSis canônico, sem importar seu domínio.

### 12.1 Módulos visuais

- Dashboard;
- Clientes;
- Sistemas;
- Assinaturas;
- Financeiro;
- Gateways;
- Integrações;
- Licenciamento;
- Configurações.

### 12.2 Dashboard

Indicadores iniciais:

- clientes ativos, inativos e bloqueados;
- assinaturas ativas por sistema;
- cobranças a vencer;
- cobranças vencidas dentro da carência;
- assinaturas bloqueadas por inadimplência;
- valor recebido no período;
- pagamentos recentes;
- emissões externas com erro;
- requisições de integração rejeitadas ou em conflito;
- últimas decisões negativas da API.

### 12.3 Perfis

| Capacidade | Administrador | Cadastro | Financeiro | Consulta |
|---|:---:|:---:|:---:|:---:|
| Consultar cadastros | Sim | Sim | Sim | Sim |
| Alterar clientes e sistemas | Sim | Sim | Não | Não |
| Gerenciar assinaturas | Sim | Sim | Não | Não |
| Consultar financeiro | Sim | Sim | Sim | Sim |
| Baixar e estornar pagamentos | Sim | Não | Sim | Não |
| Emitir e cancelar boleto/PIX | Sim | Não | Sim | Não |
| Gerenciar contas e credenciais de gateway | Sim | Não | Não | Não |
| Gerenciar credenciais da API | Sim | Não | Não | Não |
| Gerenciar integrações, escopos e políticas | Sim | Não | Não | Não |
| Consultar auditoria das integrações | Sim | Limitado | Sim | Sim |
| Gerenciar configurações | Sim | Não | Não | Não |
| Consultar auditoria | Sim | Limitado | Sim | Sim |
| Acessar Django Admin | Superusuário | Não | Não | Não |

Permissões serão verificadas no servidor. Ocultar um menu não concede nem remove autorização.

### 12.4 Rotas principais

```text
/login/
/logout/
/portal/
/portal/clientes/
/portal/sistemas/
/portal/assinaturas/
/portal/financeiro/cobrancas/
/portal/financeiro/pagamentos/
/portal/financeiro/emissoes/
/portal/gateways/
/portal/integracoes/
/portal/licenciamento/consultas/
/portal/configuracoes/
/admin/
/api/v1/licenses/check
/api/v1/payments/webhooks/<provider>/<account_public_id>/
```

Logout e ações mutáveis usarão POST e proteção CSRF. O Admin permanecerá como contingência durante a migração e será restrito a superusuários.

## 13. Segurança

- Produção usará PostgreSQL como banco autoritativo.
- `SECRET_KEY`, credenciais de banco, segredos de API e chaves privadas não ficarão no repositório.
- Credenciais e certificados das contas de gateway serão criptografados em repouso com chave externa ao banco.
- O portal nunca exibirá novamente um segredo de gateway já salvo.
- Todo tráfego externo usará TLS.
- CNPJ/CPF será validado, normalizado e mascarado em logs.
- Segredos de API serão armazenados como hash e poderão ser rotacionados.
- Segredos OAuth das integrações serão armazenados como hash e tokens terão curta duração.
- Escopos, políticas por recurso, campos permitidos e redes de origem serão validados no servidor.
- API terá rate limiting por credencial e origem.
- Tokens serão assinados, terão audiência e expiração verificadas.
- Chaves de assinatura terão rotação por `kid`.
- Webhooks terão assinatura do provedor verificada antes de qualquer mutação.
- A conta indicada na URL do webhook deverá pertencer ao provedor autenticado pelo evento.
- Pagamentos, estornos, bloqueios, configurações e credenciais terão trilha de auditoria.
- Mensagens externas não revelarão segredos ou detalhes internos desnecessários.
- Consultas financeiras e decisões serão consistentes dentro de transações adequadas.

## 14. Erros e observabilidade

O sistema deve registrar:

- falhas de autenticação sem registrar o segredo;
- requisições administrativas, itens aceitos/rejeitados, conflitos de versão e chaves idempotentes reutilizadas incorretamente;
- duração e resultado das decisões de licença;
- falhas na geração de cobranças;
- testes de conexão, emissões e cancelamentos por conta de gateway;
- webhooks recebidos, repetidos e rejeitados;
- falhas e retentativas de integração;
- alterações de configuração;
- pagamentos e estornos;
- bloqueios manuais.

Métricas recomendadas:

- taxa de decisões permitidas e bloqueadas;
- latência da API;
- erros 4xx e 5xx;
- volume, latência e rejeições por integração e endpoint;
- conflitos `409` e atraso desde o último `updated_since` consultado;
- cobranças geradas por execução;
- emissões por provedor, meio e estado;
- contas de gateway com falha de conexão ou autenticação;
- eventos financeiros pendentes ou com erro;
- quantidade de clientes em carência e inadimplentes.

## 15. Impacto no projeto atual

Antes das funcionalidades novas:

1. Confirmar se SQLite ou PostgreSQL contém os dados válidos atuais.
2. Fazer backup verificável.
3. Corrigir `ClienteSistema.__str__()` e `AcessoMaquina.__str__()`.
4. Verificar duplicidades em `ClienteSistema` antes da restrição.
5. Decidir o destino dos IDs inteiros de cliente e sistema em `AcessoMaquina`.
6. Preservar `AcessoMaquina` até entender seu uso; não apagá-lo durante a criação da nova auditoria.
7. Externalizar segredos existentes.
8. Corrigir a configuração Docker e alinhar o banco dos ambientes.
9. Adicionar Django REST Framework e bibliotecas criptográficas apenas quando a fase da API começar.
10. Validar acesso às documentações, credenciais de homologação e certificados de Efí, Sicredi e Sicoob antes de implementar os adaptadores.
11. Selecionar e configurar a biblioteca OAuth2 para Client Credentials antes da API administrativa.

## 16. Estratégia de testes

### 16.1 Modelos e constraints

- documento normalizado e único;
- códigos de sistema únicos;
- par cliente-sistema único;
- dia de vencimento entre 1 e 28;
- carência não negativa;
- valores financeiros positivos;
- idempotência de cobrança e evento externo;
- múltiplas contas por provedor e meios habilitados;
- apenas uma emissão externa ativa por cobrança.

### 16.2 Ciclos financeiros

- mensal, trimestral, semestral e anual;
- mudança de mês e ano;
- contrato com e sem término;
- geração concorrente;
- pagamento parcial, total e estorno;
- cancelamento de cobrança;
- emissão e cancelamento de boleto e PIX nos três provedores;
- falha de emissão seguida de nova tentativa;
- troca de gateway somente depois do cancelamento da emissão anterior;
- webhook repetido e fora de ordem;
- webhook roteado para conta ou provedor incorreto;
- segredo e certificado não expostos em formulário, log ou erro.

### 16.3 Limites de data

- no dia do vencimento;
- primeiro dia após o vencimento;
- último dia da carência;
- primeiro dia após a carência;
- carência zero;
- expiração do token na virada do dia e do timezone.

### 16.4 Decisão de licença

- credencial ausente, inválida, revogada e expirada;
- sistema inativo;
- cliente inexistente, inativo e bloqueado;
- assinatura inexistente, futura, expirada, inativa e bloqueada;
- cliente em dia;
- atraso dentro da carência;
- inadimplência após carência;
- precedência entre os bloqueios.

### 16.5 Token

- assinatura válida e inválida;
- emissor e audiência;
- expiração;
- chave antiga e nova durante rotação;
- adulteração do payload;
- contingência com token válido;
- recusa offline após expiração.

### 16.6 Portal e permissões

- redirecionamento de usuário anônimo;
- cada papel em cada ação sensível;
- POST e CSRF nas mutações;
- acesso direto por URL sem permissão;
- mensagens e preservação dos filtros;
- Admin restrito a superusuário.

### 16.7 Contrato dos adaptadores

- a mesma suíte de contrato executada contra Efí, Sicredi e Sicoob;
- validação de configuração obrigatória por provedor;
- emissão, consulta e cancelamento normalizados;
- transformação de webhook em pagamento interno;
- respostas e erros externos convertidos sem vazar dados sensíveis;
- testes automatizados com doubles e testes de fumaça nos ambientes de homologação.

### 16.8 Integrações administrativas

- autenticação OAuth2, expiração, rotação, escopos e rate limit;
- políticas `SCL_MASTER`, `LEGACY_MASTER` e `SHARED` por recurso;
- somente uma integração proprietária por registro e transferência auditada de propriedade;
- campos não autorizados rejeitados sem mutação parcial;
- `If-Match` válido e conflito de versão `409`;
- `external_id` único por integração e recurso;
- repetição idempotente e reutilização inválida da mesma chave;
- lotes de até 100 itens com resultados independentes;
- upsert em lote e conflito de criação individual com `external_id` existente;
- consultas paginadas e filtro `updated_since`;
- gerador interno ignorando assinaturas controladas pelo legado;
- pagamento legado refletido na próxima decisão de licença;
- integração estornando somente pagamentos criados por ela;
- dados inativados, cancelados e estornados presentes na sincronização.

## 17. Fases de entrega

### Fase 0: baseline e dados

- identificar banco autoritativo;
- criar backup e testes de caracterização;
- corrigir representações e inconsistências prioritárias;
- configurar PostgreSQL e segredos por ambiente.

### Fase 1: portal e acesso humano

- integrar shell Duralux;
- criar login, logout, templates base e navegação;
- criar papéis e permissões;
- mover Admin para `/admin/`.

### Fase 2: cadastros e assinaturas

- CRUD de clientes e sistemas;
- credenciais de sistema;
- evolução de `ClienteSistema` para assinatura;
- vigência, periodicidade, preço e bloqueios.

### Fase 3: financeiro manual

- configuração global e exceções;
- geração idempotente de cobranças;
- baixa manual, pagamento parcial e estorno;
- cadastro multi-conta de gateways e armazenamento seguro de credenciais;
- telas financeiras e indicadores.

### Fase 4: integrações administrativas

- cadastrar integrações, credenciais, escopos e políticas;
- criar referências externas e auditoria de requisições;
- implementar OAuth2 Client Credentials;
- disponibilizar consultas e mutações de clientes, assinaturas, cobranças e pagamentos;
- implementar controle de versão, idempotência e lotes controlados.

### Fase 5: licenciamento

- serviço central de decisão;
- API REST versionada;
- autenticação das credenciais;
- token RS256 diário;
- auditoria e rate limiting.

### Fase 6: robustez operacional

- dashboards completos;
- observabilidade;
- rotação de credenciais e chaves;
- testes de concorrência e carga;
- migração gradual dos usuários do Admin.

### Fase 7: integração financeira automática

- implementar e homologar os adaptadores Efí, Sicredi e Sicoob;
- emitir e cancelar boleto e PIX;
- validar assinaturas e autenticação dos webhooks;
- conciliar eventos idempotentes;
- testar indisponibilidade, repetição e troca segura de gateway.

As fases 0 a 6 podem formar um piloto interno com baixa manual. A fase 7 integra o escopo obrigatório do primeiro release de produção.

## 18. Critérios de sucesso

O design estará entregue quando:

1. A equipe interna puder cadastrar cliente, sistema e assinatura sem usar o Admin.
2. O SCL gerar cobranças corretas para as quatro periodicidades.
3. O Financeiro puder escolher uma conta Efí, Sicredi ou Sicoob ao emitir cada cobrança.
4. Boleto e PIX funcionarem conforme os meios habilitados na conta escolhida.
5. Pagamentos manuais e automáticos atualizarem imediatamente a decisão financeira.
6. Webhooks repetidos não gerarem baixas duplicadas.
7. Um legado autorizado puder consultar e alimentar clientes, assinaturas, cobranças e pagamentos.
8. Lotes parciais, idempotência e conflitos de versão não causarem duplicidade ou perda silenciosa.
9. Assinaturas externas não receberem cobranças duplicadas do gerador interno.
10. A API de licenciamento distinguir em dia, carência, inadimplência e bloqueios administrativos.
11. Um consumidor puder operar durante uma indisponibilidade curta usando token diário válido.
12. Token expirado não permitir acesso sem nova validação.
13. Todas as decisões e mutações críticas possuírem auditoria.
14. Os papéis internos impedirem ações não autorizadas no servidor.
15. Efí, Sicredi e Sicoob estiverem homologados por adaptadores independentes.

## 19. Pré-requisitos externos para produção

Efí, Sicredi e Sicoob fazem parte do primeiro release de produção. Sua implementação exige contratos bancários ativos, credenciais de homologação e produção, certificados quando aplicáveis, dados de convênio e liberação dos respectivos produtos de boleto e PIX. Essas dependências não bloqueiam cadastros, assinaturas, financeiro manual, geração de cobranças, API ou token, mas bloqueiam a homologação final da fase automática.

Cada provedor receberá uma especificação técnica própria antes da implementação do adaptador, cobrindo autenticação, certificados, endpoints, idempotência, emissão, cancelamento, consulta, webhooks e reconciliação.
