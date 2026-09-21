from django.db import models

from licencas.validators import validate_document


def normalize_document(value):
    import re

    return re.sub(r"\D", "", value or "")


# Create your models here.
class Cliente(models.Model):
    id = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=100, verbose_name='Nome')
    cnpjcpf = models.CharField(max_length=18, unique=True, verbose_name='CNPJ/CPF', validators=[validate_document])
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    email = models.EmailField(max_length=100, verbose_name='Email')
    telefone = models.CharField(max_length=30, verbose_name='Telefone')
    cep = models.CharField(max_length=9, verbose_name='CEP')
    endereco = models.CharField(max_length=100, verbose_name='Endereço')
    endnumero = models.CharField(max_length=10, verbose_name='Número')
    endbairro = models.CharField(max_length=50, verbose_name='Bairro')
    endcomplemento = models.CharField(max_length=50, verbose_name='Complemento')
    endUF = models.CharField(max_length=2, verbose_name='UF')
    endcidade = models.CharField(max_length=100, verbose_name='Cidade')
    endcodpais = models.IntegerField(verbose_name='Código País')
    endpais = models.CharField(max_length=100, verbose_name='País')
    bloqueado = models.BooleanField(default=False, verbose_name='Bloqueado')
    motivo_bloqueio = models.TextField(blank=True, default='', verbose_name='Motivo do bloqueio')
    bloqueado_em = models.DateTimeField(null=True, blank=True, verbose_name='Bloqueado em')
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    alterado_em = models.DateTimeField(auto_now=True, verbose_name='Alterado em')


    class Meta:
        ordering = ['nome']
        verbose_name = 'Cliente'

    def clean(self):
        self.cnpjcpf = normalize_document(self.cnpjcpf)
        if self.bloqueado and not (self.motivo_bloqueio or "").strip():
            from django.core.exceptions import ValidationError

            raise ValidationError({"motivo_bloqueio": "Informe o motivo do bloqueio."})

    def save(self, *args, **kwargs):
        self.cnpjcpf = normalize_document(self.cnpjcpf)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome


class Sistema(models.Model):
    id = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=100, verbose_name='Nome')
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    descricao = models.TextField(blank=True, default='', verbose_name='Descrição')
    codigo = models.SlugField(max_length=50, unique=True, verbose_name='Código')
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    alterado_em = models.DateTimeField(auto_now=True, verbose_name='Alterado em')

    class Meta:
        ordering = ['nome']
        verbose_name = 'Sistema'

    def __str__(self):
        return self.nome


class ClienteSistema(models.Model):
    class Periodicidade(models.TextChoices):
        MENSAL = "monthly", "Mensal"
        TRIMESTRAL = "quarterly", "Trimestral"
        SEMESTRAL = "semiannual", "Semestral"
        ANUAL = "annual", "Anual"

    id = models.AutoField(primary_key=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='clientes', verbose_name='Cliente')
    sistema = models.ForeignKey(Sistema, on_delete=models.PROTECT, related_name='sistemas', verbose_name='Sistema')
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    valor_recorrente = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Valor recorrente')
    periodicidade = models.CharField(max_length=10, choices=Periodicidade.choices, verbose_name='Periodicidade')
    data_inicio = models.DateField(verbose_name='Início')
    data_fim = models.DateField(null=True, blank=True, verbose_name='Fim')
    primeiro_vencimento = models.DateField(verbose_name='Primeiro vencimento')
    bloqueado = models.BooleanField(default=False, verbose_name='Bloqueado')
    motivo_bloqueio = models.TextField(blank=True, default='', verbose_name='Motivo do bloqueio')
    bloqueado_em = models.DateTimeField(null=True, blank=True, verbose_name='Bloqueado em')
    dia_vencimento = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name='Dia de vencimento')
    dias_carencia = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name='Dias de carência')
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    alterado_em = models.DateTimeField(auto_now=True, verbose_name='Alterado em')

    class Meta:
        ordering = ['cliente', 'sistema']
        verbose_name = 'Assinatura'
        verbose_name_plural = 'Assinaturas'
        constraints = [
            models.UniqueConstraint(
                fields=("cliente", "sistema"),
                name="clientesistema_unique_par",
            ),
            models.CheckConstraint(
                condition=models.Q(dia_vencimento__gte=1) & models.Q(dia_vencimento__lte=28),
                name="assinatura_dia_vencimento_1_28",
            ),
            models.CheckConstraint(
                condition=models.Q(dias_carencia__gte=0),
                name="assinatura_carencia_nao_negativa",
            ),
            models.CheckConstraint(
                condition=models.Q(ativo=False) | models.Q(valor_recorrente__gt=0),
                name="assinatura_valor_positivo_quando_ativa",
            ),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        errors = {}
        if self.dia_vencimento is not None and not (1 <= self.dia_vencimento <= 28):
            errors["dia_vencimento"] = "Use um dia de vencimento entre 1 e 28."
        if self.data_fim and self.data_inicio and self.data_fim < self.data_inicio:
            errors["data_fim"] = "A data de fim não pode ser antes do início."
        if self.bloqueado and not (self.motivo_bloqueio or "").strip():
            errors["motivo_bloqueio"] = "Informe o motivo do bloqueio."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.cliente} - {self.sistema}"

class AcessoMaquina(models.Model):
    id = models.AutoField(primary_key=True)
    cliente = models.IntegerField (verbose_name='Cliente')
    sistema = models.IntegerField(verbose_name='Sistema')
    sistemaversao = models.CharField(max_length=20, verbose_name='Versão')
    usuario = models.CharField(max_length=200, verbose_name='Usuário')
    estacaonome = models.CharField(max_length=200, verbose_name='Estação')
    estacaomemoria = models.CharField(max_length=50, verbose_name='Memória')
    estacaoprocessador = models.CharField(max_length=200, verbose_name='Processador')
    estacaosistemaoperacional = models.CharField(max_length=200, verbose_name='Sistema Operacional')
    estacaomac = models.CharField(max_length=100, verbose_name='MAC')
    acessoip = models.CharField(max_length=20, verbose_name='IP')
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    alterado_em = models.DateTimeField(auto_now=True, verbose_name='Alterado em')

    class Meta:
        ordering = ['cliente', 'sistema']
        verbose_name = 'Acesso'

    def __str__(self):
        return f"Cliente {self.cliente} - Sistema {self.sistema}"
