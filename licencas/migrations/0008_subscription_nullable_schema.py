from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("licencas", "0007_document_unique_and_sistema_codigo_unique"),
    ]

    operations = [
        migrations.AddField(
            model_name="clientesistema",
            name="valor_recorrente",
            field=models.DecimalField(decimal_places=2, max_digits=12, null=True, verbose_name="Valor recorrente"),
        ),
        migrations.AddField(
            model_name="clientesistema",
            name="periodicidade",
            field=models.CharField(blank=True, max_length=10, null=True, verbose_name="Periodicidade"),
        ),
        migrations.AddField(
            model_name="clientesistema",
            name="data_inicio",
            field=models.DateField(null=True, verbose_name="Início"),
        ),
        migrations.AddField(
            model_name="clientesistema",
            name="data_fim",
            field=models.DateField(blank=True, null=True, verbose_name="Fim"),
        ),
        migrations.AddField(
            model_name="clientesistema",
            name="primeiro_vencimento",
            field=models.DateField(null=True, verbose_name="Primeiro vencimento"),
        ),
        migrations.AddField(
            model_name="clientesistema",
            name="bloqueado",
            field=models.BooleanField(default=False, verbose_name="Bloqueado"),
        ),
        migrations.AddField(
            model_name="clientesistema",
            name="motivo_bloqueio",
            field=models.TextField(blank=True, default="", verbose_name="Motivo do bloqueio"),
        ),
        migrations.AddField(
            model_name="clientesistema",
            name="bloqueado_em",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Bloqueado em"),
        ),
        migrations.AddField(
            model_name="clientesistema",
            name="dia_vencimento",
            field=models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="Dia de vencimento"),
        ),
        migrations.AddField(
            model_name="clientesistema",
            name="dias_carencia",
            field=models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="Dias de carência"),
        ),
        migrations.AlterModelOptions(
            name="clientesistema",
            options={"ordering": ["cliente", "sistema"], "verbose_name": "Assinatura", "verbose_name_plural": "Assinaturas"},
        ),
        migrations.AddConstraint(
            model_name="clientesistema",
            constraint=models.UniqueConstraint(
                fields=("cliente", "sistema"),
                name="clientesistema_unique_par",
            ),
        ),
        migrations.AddConstraint(
            model_name="clientesistema",
            constraint=models.CheckConstraint(
                condition=models.Q(dia_vencimento__gte=1) & models.Q(dia_vencimento__lte=28),
                name="assinatura_dia_vencimento_1_28",
            ),
        ),
        migrations.AddConstraint(
            model_name="clientesistema",
            constraint=models.CheckConstraint(
                condition=models.Q(dias_carencia__gte=0),
                name="assinatura_carencia_nao_negativa",
            ),
        ),
    ]
