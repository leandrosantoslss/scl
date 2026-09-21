
# Rollback

Classificar migrações: reversível (rollback de schema) ou require-restore.
1. Rollback de imagem para a versão anterior.
2. Feature DISABLED.
3. Backup com restore se necessário (manual decisão).
4. Rollback das chaves de JWT (kid antigo) preservado.
5. Pausa de webhooks caso restore exigido.
