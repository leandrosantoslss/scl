# Plano: diagnóstico inicial do SCL

## Objetivo
Mapear o estado atual do projeto Django SCL, o design system disponível e os pontos de migração do Django Admin para um portal próprio, sem alterar o código legado nesta etapa.

## Próximo passo
Após o usuário liberar os caminhos do legado em `.reversa/reversa-config.json`, executar o Gate 0 e o Plano 01. Nenhuma migração pode ocorrer antes da identificação do banco autoritativo e da restauração testada do backup.

## Fases

### Fase 1: Inventário técnico
- [x] Mapear estrutura e dependências
- [x] Identificar configuração e entry points
- **Status:** complete

### Fase 2: Domínio e comportamento atual
- [x] Mapear modelos, permissões e operações no admin
- [x] Mapear testes e riscos existentes
- **Status:** complete

### Fase 3: Design system e referências
- [x] Inventariar o design system local
- [x] Comparar `controlelicenca`, `ekklesiafiscal` e exclusivamente o LoteSis em `C:\Users\leand\projetos\lotesis`
- **Status:** complete

### Fase 4: Síntese
- [x] Documentar arquitetura atual
- [x] Propor sequência segura para a migração ao portal
- **Status:** complete

### Fase 5: Redefinição do domínio SCL
- [x] Separar o SCL das regras do projeto ControleLicença
- [x] Definir assinatura e cobrança por cliente-sistema
- [x] Definir vencimento, carência e bloqueios
- [x] Definir API diária e token assinado
- [x] Definir portal, papéis, segurança e fases
- [x] Registrar e autorrevisar a especificação
- [x] Obter revisão final do usuário
- **Status:** complete

### Fase 6: Planejamento de implementação
- [x] Criar roadmap e oito planos por subsistema
- [x] Revisar cobertura contra a especificação aprovada
- [x] Corrigir gates de banco, migração, auditoria, autoridade, segurança, concorrência e rollout
- [x] Registrar bloqueios de edição, Git e homologação bancária
- **Status:** complete

## Decisões
| Decisão | Motivo |
|---|---|
| Diagnóstico somente leitura no legado | O usuário pediu análise antes das implementações |
| Artefatos de análise em `_reversa_sdd/analysis-scl/` | Preserva o projeto legado e segue a política do workspace |
| LoteSis canônico: `C:\Users\leand\projetos\lotesis` | Caminho confirmado pelo usuário; variantes com nomes semelhantes ficam fora das decisões |
| Portal Django server-rendered | É o padrão de menor complexidade e maior reaproveitamento entre as referências |
| Admin permanecerá temporariamente em `/admin/` | Permite migração gradual e fallback operacional |
| Regras do ControleLicença não serão reutilizadas | Os nomes são semelhantes, mas os domínios são diferentes |
| Cobrança por cliente-sistema | Cada sistema contratado possui preço, periodicidade e situação financeira próprios |
| Token diário RS256, sem MD5 | Permite contingência verificável sem expor segredo de assinatura ao consumidor |
| Cadastro multi-conta de gateways | Efí, Sicredi e Sicoob podem coexistir, com escolha da conta em cada cobrança |
| Emissão externa separada da cobrança | Preserva tentativas, cancelamentos, troca segura de gateway e idempotência |
| API administrativa separada da API de licença | Sistemas legados podem consultar e alimentar dados sem reutilizar credenciais dos produtos licenciados |
| Autoridade configurável por integração e recurso | Permite SCL, legado ou modo compartilhado sem política implícita de última gravação |
| Uma origem geradora por assinatura | Evita que SCL e legado criem parcelas duplicadas |
| Lotes de até 100 itens | Viabiliza carga inicial com resultado e idempotência por item |
| Gate 0 antes de qualquer migração | Obriga identificação do PostgreSQL autoritativo, inventário, backup e restauração testada |
| Rate limit atômico em PostgreSQL | Mantém os limites por credencial e origem consistentes entre múltiplos workers |
| Release bloqueado pelos três provedores | Efí, Sicredi e Sicoob precisam de specs, planos, implementação e homologação das capacidades contratadas |

## Erros encontrados
| Erro | Tentativa | Tratamento |
|---|---:|---|
| A pasta SCL não é um repositório Git | 1 | Registrar a ausência de histórico/diff e continuar em modo somente leitura |
| Patch inicial da revisão de gateways não encontrou um trecho do portal | 1 | Dividir a atualização em blocos menores e verificar cada seção |
| Cliente `sqlite3` não está instalado | 1 | Consultar o SQLite local com a biblioteca padrão do Python; contagens confirmadas como zero |
