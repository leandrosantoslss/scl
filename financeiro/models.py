from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class ConfiguracaoFinanceira(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    dia_vencimento = models.PositiveSmallIntegerField(default=5, verbose_name="Dia de vencimento")
    dias_carencia = models.PositiveSmallIntegerField(default=0, verbose_name="Dias de carência")
    timezone = models.CharField(max_length=64, default="America/Sao_Paulo", verbose_name="Fuso horário")
    alterado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="configuracoes_financeiras_alteradas",
    )
    alterado_em = models.DateTimeField(auto_now=True, verbose_name="Alterado em")

    class Meta:
        verbose_name = "Configuração financeira"
        constraints = [
            models.CheckConstraint(
                condition=Q(dia_vencimento__gte=1) & Q(dia_vencimento__lte=28),
                name="finance_config_dia_vencimento_1_28",
            ),
            models.CheckConstraint(
                condition=Q(dias_carencia__gte=0),
                name="finance_config_carencia_nao_negativa",
            ),
            models.CheckConstraint(
                condition=Q(pk=1),
                name="finance_config_singleton_pk",
            ),
        ]

    def save(self, *args, **kwargs):
        self.pk = 1
        return super().save(*args, **kwargs)

    def clean(self):
        if not (1 <= self.dia_vencimento <= 28):
            raise ValidationError({"dia_vencimento": "Use um dia entre 1 e 28."})
        if self.dias_carencia < 0:
            raise ValidationError({"dias_carencia": "A carência não pode ser negativa."})

    def __str__(self):
        return f"Vencimento dia {self.dia_vencimento}, carência {self.dias_carencia}d"


class Cobranca(models.Model):
    class Status(models.TextChoices):
        ABERTA = "aberta", "Aberta"
        PAGA = "paga", "Paga"
        CANCELADA = "cancelada", "Cancelada"

    assinatura = models.ForeignKey(
        "licencas.ClienteSistema",
        on_delete=models.PROTECT,
        related_name="cobrancas",
        verbose_name="Assinatura",
    )
    competencia = models.DateField(verbose_name="Competência")
    vencimento = models.DateField(verbose_name="Vencimento")
    fim_carencia = models.DateField(verbose_name="Fim da carência")
    valor_original = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Valor original")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ABERTA, verbose_name="Status")
    descricao = models.CharField(max_length=255, blank=True, default="", verbose_name="Descrição")
    origem = models.CharField(max_length=16, default="scl", verbose_name="Origem")
    cancelada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cobrancas_canceladas",
    )
    cancelada_em = models.DateTimeField(null=True, blank=True)
    motivo_cancelamento = models.TextField(blank=True, default="")
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    alterado_em = models.DateTimeField(auto_now=True, verbose_name="Alterado em")

    class Meta:
        verbose_name = "Cobrança"
        verbose_name_plural = "Cobranças"
        ordering = ["vencimento", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=("assinatura", "competencia"),
                name="cobranca_assinatura_competencia_unica",
            ),
            models.CheckConstraint(
                condition=Q(valor_original__gt=0),
                name="cobranca_valor_positivo",
            ),
            models.CheckConstraint(
                condition=Q(fim_carencia__gte=models.F("vencimento")),
                name="cobranca_carencia_apos_vencimento",
            ),
        ]

    def clean(self):
        if self.valor_original is not None and self.valor_original <= 0:
            raise ValidationError({"valor_original": "O valor deve ser positivo."})
        if self.fim_carencia and self.vencimento and self.fim_carencia < self.vencimento:
            raise ValidationError({"fim_carencia": "O fim da carência não pode ser antes do vencimento."})

    def __str__(self):
        return f"{self.assinatura} — {self.competencia}"


class ContaGateway(models.Model):
    class Provider(models.TextChoices):
        EFI = "efi", "Efí"
        SICREDI = "sicredi", "Sicredi"
        SICOOB = "sicoob", "Sicoob"

    class Ambiente(models.TextChoices):
        SANDBOX = "sandbox", "Sandbox"
        PRODUCAO = "producao", "Produção"

    public_id = models.UUIDField(default=uuid4, unique=True, editable=False)
    nome = models.CharField(max_length=100, verbose_name="Nome")
    provedor = models.CharField(max_length=16, choices=Provider.choices, verbose_name="Provedor")
    ambiente = models.CharField(max_length=16, choices=Ambiente.choices, default=Ambiente.SANDBOX, verbose_name="Ambiente")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    habilita_boleto = models.BooleanField(default=False, verbose_name="Boleto")
    habilita_pix = models.BooleanField(default=False, verbose_name="PIX")
    configuracao_publica = models.JSONField(default=dict, blank=True, verbose_name="Configuração pública")
    configuracao_criptografada = models.TextField(blank=True, default="", verbose_name="Configuração criptografada")
    ultima_conexao_status = models.CharField(max_length=64, blank=True, default="", verbose_name="Última conexão")
    ultima_conexao_em = models.DateTimeField(null=True, blank=True, verbose_name="Última conexão em")
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="contas_gateway_criadas")
    alterado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="contas_gateway_alteradas")
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    alterado_em = models.DateTimeField(auto_now=True, verbose_name="Alterado em")

    class Meta:
        verbose_name = "Conta de gateway"
        verbose_name_plural = "Contas de gateway"
        ordering = ["provedor", "nome"]

    def clean(self):
        if self.habilita_boleto is False and self.habilita_pix is False:
            raise ValidationError("Habilite boleto, PIX ou ambos nesta conta.")

    def __str__(self):
        return f"{self.provedor}/{self.ambiente} — {self.nome}"


class EmissaoCobranca(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Solicitada"
        ISSUED = "issued", "Emitida"
        PAID = "paid", "Paga"
        CANCELLED = "cancelled", "Cancelada"
        FAILED = "failed", "Falhou"
        PENDING_UNKNOWN = "pending_unknown", "Pendente desconhecido"

    cobranca = models.ForeignKey(
        Cobranca, on_delete=models.PROTECT, related_name="emissoes", verbose_name="Cobrança"
    )
    conta = models.ForeignKey(
        ContaGateway, on_delete=models.PROTECT, related_name="emissoes", verbose_name="Conta"
    )
    meio = models.CharField(max_length=10, verbose_name="Meio")
    chave_idempotencia = models.CharField(max_length=100, unique=True, verbose_name="Chave de idempotência")
    id_externo = models.CharField(max_length=128, null=True, blank=True, verbose_name="ID externo")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.REQUESTED, verbose_name="Status")
    vencimento_externo = models.DateField(null=True, blank=True)
    boleto_url = models.CharField(max_length=500, null=True, blank=True)
    linha_digitavel = models.CharField(max_length=100, null=True, blank=True)
    pix_copia_e_cola = models.TextField(null=True, blank=True)
    erro_normalizado = models.CharField(max_length=255, blank=True, default="", verbose_name="Erro normalizado")
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    alterado_em = models.DateTimeField(auto_now=True, verbose_name="Alterado em")

    class Meta:
        verbose_name = "Emissão de cobrança"
        verbose_name_plural = "Emissões de cobrança"
        ordering = ["-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=("cobranca",),
                condition=Q(status__in=("requested", "issued")),
                name="emissao_ativa_unica_por_cobranca",
            ),
            models.UniqueConstraint(
                fields=("conta", "id_externo"),
                condition=~Q(id_externo="") & ~Q(id_externo=None),
                name="emissao_id_externo_por_conta_unico",
            ),
        ]


class EventoGateway(models.Model):
    class Status(models.TextChoices):
        PROCESSADO = "processado", "Processado"
        DUPLICADO = "duplicado", "Duplicado"
        ERRO = "erro", "Erro"
        IGNORADO = "ignorado", "Ignorado"

    conta = models.ForeignKey(
        ContaGateway, on_delete=models.PROTECT, related_name="eventos", verbose_name="Conta"
    )
    provedor = models.CharField(max_length=16, verbose_name="Provedor")
    id_evento_externo = models.CharField(max_length=200, verbose_name="ID do evento externo")
    tipo = models.CharField(max_length=50, verbose_name="Tipo")
    payload_hash = models.CharField(max_length=64, verbose_name="Hash do payload")
    payload_protegido = models.JSONField(
        default=dict,
        blank=True,
        help_text="Snapshot sem segredos, itens pessoais ou valores completos.",
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PROCESSADO, verbose_name="Status")
    tentativas = models.PositiveSmallIntegerField(default=0, verbose_name="Tentativas")
    erro = models.TextField(blank=True, default="", verbose_name="Erro")
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    class Meta:
        verbose_name = "Evento de gateway"
        verbose_name_plural = "Eventos de gateway"
        ordering = ["-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=("provedor", "id_evento_externo"),
                name="evento_gateway_provedor_evento_unico",
            ),
        ]


class Pagamento(models.Model):
    class Origem(models.TextChoices):
        MANUAL = "manual", "Manual"
        GATEWAY = "gateway", "Gateway"
        LEGACY = "legacy", "Legado"

    class Status(models.TextChoices):
        CONFIRMED = "confirmed", "Confirmado"
        REVERSED = "reversed", "Estornado"

    cobranca = models.ForeignKey(
        Cobranca,
        on_delete=models.PROTECT,
        related_name="pagamentos",
        verbose_name="Cobrança",
    )
    valor = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Valor")
    pago_em = models.DateTimeField(verbose_name="Pago em")
    forma = models.CharField(max_length=30, verbose_name="Forma")
    origem = models.CharField(max_length=16, choices=Origem.choices, verbose_name="Origem")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.CONFIRMED, verbose_name="Status")
    identificador_externo = models.CharField(max_length=128, null=True, blank=True, verbose_name="Identificador externo")
    emissao_gateway = models.ForeignKey(
        "EmissaoCobranca",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="pagamentos",
    )
    provedor_gateway = models.CharField(max_length=16, null=True, blank=True)
    integracao = models.ForeignKey(
        "integracoes.IntegracaoLegado",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="pagamentos",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pagamentos_registrados",
    )
    estornado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pagamentos_estornados",
    )
    estornado_em = models.DateTimeField(null=True, blank=True)
    motivo_estorno = models.TextField(blank=True, default="")
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    alterado_em = models.DateTimeField(auto_now=True, verbose_name="Alterado em")

    class Meta:
        verbose_name = "Pagamento"
        verbose_name_plural = "Pagamentos"
        ordering = ["pago_em", "pk"]
        constraints = [
            models.CheckConstraint(
                condition=Q(valor__gt=0),
                name="pagamento_valor_positivo",
            ),
            models.UniqueConstraint(
                fields=("provedor_gateway", "identificador_externo"),
                condition=Q(origem="gateway"),
                name="pagamento_gateway_provedor_externo_unico",
            ),
            models.CheckConstraint(
                condition=~Q(origem="gateway")
                | (Q(emissao_gateway__isnull=False) & Q(provedor_gateway__isnull=False)),
                name="pagamento_gateway_tem_proveniencia",
            ),
            models.UniqueConstraint(
                fields=("integracao", "identificador_externo"),
                condition=Q(origem="legacy"),
                name="pagamento_legado_integracao_externo_unico",
            ),
            models.CheckConstraint(
                condition=~Q(origem="legacy") | Q(integracao__isnull=False),
                name="pagamento_legado_tem_integracao",
            ),
        ]
