
# Deploy

1. Backup.
2. Aviso manutenção.
3. Imagem criada.
4. Migração explícita via job (nunca automática no processo web).
5. `collectstatic`.
6. Rollout web com Gunicorn.
7. Health check `/health/`.
8. Ativação do scheduler de cobranças (00:15 America/São_Paulo com lock distribuído).
