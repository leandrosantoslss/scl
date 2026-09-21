
# Backup e restauração

1. Backup: `pg_dump --format=custom` database autoritativo; checksum + cópia encriptada.
2. Restauração: `pg_restore --clean --if-exists` em banco separado de validação.
3. Comparação de contagem das tabelas por domínio; smoke tests somente leitura.
4. Gate de deploy: só prosseguir se restauração testada estiver VERDE.
