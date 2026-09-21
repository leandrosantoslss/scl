from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("licencas", "0009_derive_subscription_data"),
    ]

    operations = [
        migrations.AlterField(
            model_name="clientesistema",
            name="valor_recorrente",
            field=models.DecimalField(decimal_places=2, max_digits=12, verbose_name="Valor recorrente"),
        ),
        migrations.AlterField(
            model_name="clientesistema",
            name="periodicidade",
            field=models.CharField(max_length=10, verbose_name="Periodicidade"),        ),
        migrations.AlterField(
            model_name="clientesistema",
            name="data_inicio",
            field=models.DateField(verbose_name="Início"),
        ),
        migrations.AlterField(
            model_name="clientesistema",
            name="primeiro_vencimento",
            field=models.DateField(verbose_name="Primeiro vencimento"),
        ),
        migrations.AddConstraint(
            model_name="clientesistema",
            constraint=models.CheckConstraint(
                condition=models.Q(ativo=False) | models.Q(valor_recorrente__gt=0),
                name="assinatura_valor_positivo_quando_ativa",
            ),
        ),
    ]
