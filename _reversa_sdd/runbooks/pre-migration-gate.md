# Gate 0: banco autoritativo e pré-migração

**Data:** 2026-09-20
**Status:** FECHADO - condições registradas e aprovadas pelo operador

## Decisão do operador

- Banco autoritativo: PostgreSQL externo em `easypanel.lotesis.cloud:35432` (servidor `17.11`), banco `DBSCL`.
- Banco de testes descartável: mesmo servidor, banco `SCL_TEST_DB`; distinto do autoritativo.
- Ambos os bancos foram criados vazios durante este gate via `create-postgres-databases.ps1` (idempotente, sem criação de tabelas).
- SQLite local: somente evidência legada local; não é alvo de produção.
- Diretório `data/db/`: não autoritativo, permanece intocado e não foi inspecionado.
- `AcessoMaquina`: preservar como histórico nesta fase; não excluir nem alterar sua estrutura.
- Credencial exposta acidentalmente em log de sessão foi rotacionada pelo operador antes da validação.

## Evidência local

| Tabela | Linhas no `db.sqlite3` |
|---|---:|
| `licencas_cliente` | 0 |
| `licencas_sistema` | 0 |
| `licencas_clientesistema` | 0 |
| `licencas_acessomaquina` | 0 |

## Evidência do PostgreSQL autoritativo (validação somente leitura, sem imprimir credenciais)

```json
{"database": "DBSCL", "server_version": "17.11 (Debian 17.11-1.pgdg13+2)", "public_tables": [], "table_counts": {"licencas_acessomaquina": null, "licencas_cliente": null, "licencas_clientesistema": null, "licencas_sistema": null}, "test_database": "SCL_TEST_DB", "test_server_version": "17.11 (Debian 17.11-1.pgdg13+2)"}
```

## Pré-requisitos

- [x] Substituir todos os `CHANGE_ME` e hosts simbólicos no `.env`.
- [x] Validar nome, versão e conectividade do PostgreSQL autoritativo sem imprimir credenciais.
- [x] Inventariar contagens das tabelas no PostgreSQL autoritativo (schema público vazio).
- [x] Executar `pg_dump --format=custom` e calcular checksum — não aplicável: bancos criados vazios neste gate, sem dados ou objetos a preservar.
- [x] Restaurar o backup em banco separado de validação — não aplicável pela mesma razão.
- [x] Comparar contagens e executar smoke tests somente leitura (inventário completo do schema público vazio).
- [x] Registrar evidências e aprovação do operador.

## Compromissos obrigatórios seguintes

- Backup `pg_dump` com checksum e restauração testada é exigido antes do primeiro deploy com dados reais (runbooks do Plano 08) e antes de qualquer migração aplicada a banco não vazio.
- Toda migração/mutação de dados usará `DATABASE_URL` explícito; o alvo autoritativo e o banco de testes permanecem distintos.
- `SCL_TEST_DB` é descartável e pode ser recriado pelos testes; `DBSCL` não recebe dados de produção até existir backup comprovado.

## Ferramentas observadas

- O WSL não possui `psql`, `pg_dump` ou integração ativa com Docker Desktop.
- O Python do Windows (3.13.9) possui Django 5.2.11, jazzmin, dateutil, yaml e psycopg2 2.9.11; pytest/pytest-django/django-environ instalados durante este gate.
- Não foi encontrado cliente PostgreSQL em `C:\Program Files\PostgreSQL`.

Nenhuma migração foi executada até o fechamento deste gate.
