from uuid import uuid4

from django.conf import settings
from django.db import models


class AuthorityMode(models.TextChoices):
    SCL_MASTER = "scl_master", "SCL"
    LEGACY_MASTER = "legacy_master", "Legado"
    SHARED = "shared", "Compartilhado"


class Recurso(models.TextChoices):
    CLIENTE = "client", "Cliente"
    ASSINATURA = "subscription", "Assinatura"
    COBRANCA = "charge", "Cobrança"
    PAGAMENTO = "payment", "Pagamento"


class IntegracaoLegado(models.Model):
    public_id = models.UUIDField(default=uuid4, unique=True, editable=False)
    nome = models.CharField(max_length=100, unique=True)
    application = models.OneToOneField(
        "oauth2_provider.Application",
        on_delete=models.PROTECT,
        related_name="integracao_legado",
    )
    ativo = models.BooleanField(default=True)
    escopos = models.JSONField(default=list, blank=True)
    limite_requisicoes = models.PositiveIntegerField(
        default=60,
        help_text="Requisições por minuto (1 a 10000).",
    )
    redes_permitidas = models.JSONField(
        default=list,
        blank=True,
        help_text="Lista de CIDRs; vazio permite qualquer origem.",
    )
    credencial_expira_em = models.DateTimeField(null=True, blank=True)
    ultimo_uso_em = models.DateTimeField(null=True, blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="integracoes_criadas",
    )
    alterado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="integracoes_alteradas",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    alterado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Integração legada"
        verbose_name_plural = "Integrações legadas"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class PoliticaIntegracao(models.Model):
    integration = models.ForeignKey(
        IntegracaoLegado, on_delete=models.CASCADE, related_name="politicas"
    )
    recurso = models.CharField(max_length=16, choices=Recurso.choices)
    modo = models.CharField(max_length=16, choices=AuthorityMode.choices)
    readable_fields = models.JSONField(default=list, blank=True)
    writable_fields = models.JSONField(default=list, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    alterado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Política de integração"
        verbose_name_plural = "Políticas de integração"
        constraints = [
            models.UniqueConstraint(
                fields=("integration", "recurso"),
                name="politica_integracao_recurso_unico",
            )
        ]

    def __str__(self):
        return f"{self.integration} — {self.recurso} ({self.modo})"


class ReferenciaExternaBase(models.Model):
    integration = models.ForeignKey(
        IntegracaoLegado, on_delete=models.PROTECT, related_name="%(class)ss"
    )
    external_id = models.CharField(max_length=128)
    proprietaria = models.BooleanField(default=False)
    versao_externa = models.CharField(max_length=64, null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    alterado_em = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=("integration", "external_id"),
                name="%(app_label)s_%(class)s_integracao_externo_unico",
            ),
        ]


class ClienteReferenciaExterna(ReferenciaExternaBase):
    cliente = models.ForeignKey(
        "licencas.Cliente", on_delete=models.PROTECT, related_name="referencias_externas"
    )

    class Meta(ReferenciaExternaBase.Meta):
        verbose_name = "Referência externa de cliente"
        constraints = ReferenciaExternaBase.Meta.constraints + [
            models.UniqueConstraint(
                fields=("cliente",),
                condition=models.Q(proprietaria=True),
                name="cliente_referencia_proprietaria_unica",
            ),
        ]

    def __str__(self):
        return f"{self.integration} → cliente {self.cliente_id} ({self.external_id})"


class AssinaturaReferenciaExterna(ReferenciaExternaBase):
    assinatura = models.ForeignKey(
        "licencas.ClienteSistema", on_delete=models.PROTECT, related_name="referencias_externas"
    )

    class Meta(ReferenciaExternaBase.Meta):
        verbose_name = "Referência externa de assinatura"
        constraints = ReferenciaExternaBase.Meta.constraints + [
            models.UniqueConstraint(
                fields=("assinatura",),
                condition=models.Q(proprietaria=True),
                name="assinatura_referencia_proprietaria_unica",
            ),
        ]

    def __str__(self):
        return f"{self.integration} → assinatura {self.assinatura_id} ({self.external_id})"


class CobrancaReferenciaExterna(ReferenciaExternaBase):
    cobranca = models.ForeignKey(
        "financeiro.Cobranca", on_delete=models.PROTECT, related_name="referencias_externas"
    )

    class Meta(ReferenciaExternaBase.Meta):
        verbose_name = "Referência externa de cobrança"
        constraints = ReferenciaExternaBase.Meta.constraints + [
            models.UniqueConstraint(
                fields=("cobranca",),
                condition=models.Q(proprietaria=True),
                name="cobranca_referencia_proprietaria_unica",
            ),
        ]

    def __str__(self):
        return f"{self.integration} → cobrança {self.cobranca_id} ({self.external_id})"


class PagamentoReferenciaExterna(ReferenciaExternaBase):
    pagamento = models.ForeignKey(
        "financeiro.Pagamento", on_delete=models.PROTECT, related_name="referencias_externas"
    )

    class Meta(ReferenciaExternaBase.Meta):
        verbose_name = "Referência externa de pagamento"
        constraints = ReferenciaExternaBase.Meta.constraints + [
            models.UniqueConstraint(
                fields=("pagamento",),
                condition=models.Q(proprietaria=True),
                name="pagamento_referencia_proprietaria_unica",
            ),
        ]

    def __str__(self):
        return f"{self.integration} → pagamento {self.pagamento_id} ({self.external_id})"


class AssinaturaOrigemCobranca(models.Model):
    assinatura = models.OneToOneField(
        "licencas.ClienteSistema",
        on_delete=models.CASCADE,
        related_name="origem_cobranca",
    )
    integracao = models.ForeignKey(
        IntegracaoLegado, on_delete=models.PROTECT, related_name="assinaturas_sob_origem"
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    alterado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Origem de cobrança da assinatura"

    def __str__(self):
        return f"{self.assinatura} ← {self.integracao}"


class RequisicaoIntegracao(models.Model):
    class Estado(models.TextChoices):
        EM_PROCESSAMENTO = "in_progress", "Em processamento"
        CONCLUIDA = "completed", "Concluída"

    integration = models.ForeignKey(
        IntegracaoLegado, on_delete=models.CASCADE, related_name="requisicoes"
    )
    request_id = models.CharField(max_length=64)
    chave_idempotencia = models.CharField(max_length=200, null=True, blank=True)
    metodo = models.CharField(max_length=10)
    endpoint = models.CharField(max_length=255)
    payload_hash = models.CharField(max_length=64, blank=True, default="")
    estado = models.CharField(max_length=16, choices=Estado.choices, default=Estado.EM_PROCESSAMENTO)
    resposta_snapshot = models.JSONField(default=dict, blank=True)
    itens_recebidos = models.PositiveIntegerField(default=0)
    itens_aceitos = models.PositiveIntegerField(default=0)
    itens_rejeitados = models.PositiveIntegerField(default=0)
    http_status = models.PositiveIntegerField(null=True, blank=True)
    iniciada_em = models.DateTimeField(auto_now_add=True)
    concluida_em = models.DateTimeField(null=True, blank=True)
    ip = models.CharField(max_length=64, blank=True, default="")
    erro = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        verbose_name = "Requisição de integração"
        verbose_name_plural = "Requisições de integração"
        ordering = ["-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=("integration", "chave_idempotencia"),
                condition=~models.Q(chave_idempotencia="") & ~models.Q(chave_idempotencia=None),
                name="requisicao_idempotencia_por_integracao_unica",
            ),
        ]

    def __str__(self):
        return f"{self.integration} {self.metodo} {self.endpoint}"
