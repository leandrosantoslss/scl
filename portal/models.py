import uuid

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models


class NoUpdateManager(models.Manager):
    def delete(self, *args, **kwargs):
        raise ObjectDoesNotExist("EventoAuditoria é append-only.")


class EventoAuditoria(models.Model):
    class Origem(models.TextChoices):
        PORTAL = "portal", "Portal"
        INTEGRACAO = "integration", "Integração"
        SISTEMA = "system", "Sistema"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="eventos_auditoria",
    )
    origem = models.CharField(max_length=16, choices=Origem.choices)
    origem_identificador = models.CharField(max_length=255, null=True, blank=True)
    acao = models.CharField(max_length=100)
    objeto_tipo = models.CharField(max_length=100)
    objeto_id = models.CharField(max_length=100)
    antes = models.JSONField(null=True, blank=True)
    depois = models.JSONField(null=True, blank=True)
    motivo = models.TextField(null=True, blank=True)
    request_id = models.CharField(max_length=64, null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em", "-pk"]
        verbose_name = "Evento de auditoria"
        verbose_name_plural = "Eventos de auditoria"

    objects = NoUpdateManager()

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("EventoAuditoria é imutável.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("EventoAuditoria é imutável.")

    def __str__(self):
        return f"{self.acao} ({self.objeto_tipo} {self.objeto_id})"


class JanelaRateLimit(models.Model):
    """Buckets atômicos compartilhados por todos os processos/workers."""

    scope = models.CharField(max_length=32)
    key_hash = models.CharField(max_length=64)
    window_start = models.DateTimeField()
    contagem = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Janela de rate limit"
        constraints = [
            models.UniqueConstraint(
                fields=("scope", "key_hash", "window_start"),
                name="rate_limit_bucket_unico",
            ),
        ]

    def __str__(self):
        return f"{self.scope}/{self.key_hash[:8]}@{self.window_start:%Y%m%dT%H%M}"



class Notificacao(models.Model):
    """Notificação in-app (badge no topbar), padronizada no LoteSis."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notificacoes",
    )
    titulo = models.CharField(max_length=200)
    mensagem = models.TextField()
    url = models.CharField(max_length=255, blank=True, default="")
    lida = models.BooleanField(default=False)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Notificação"
        verbose_name_plural = "Notificações"
        ordering = ["-id"]

    def __str__(self):
        return f"{self.titulo} — {self.usuario}"
