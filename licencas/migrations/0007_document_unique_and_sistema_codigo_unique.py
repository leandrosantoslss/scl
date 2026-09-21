import licencas.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("licencas", "0006_normalize_documents_populate_system_codes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="cliente",
            name="cnpjcpf",
            field=models.CharField(
                max_length=18,
                unique=True,
                validators=[licencas.validators.validate_document],
                verbose_name="CNPJ/CPF",
            ),
        ),
        migrations.AlterField(
            model_name="sistema",
            name="codigo",
            field=models.SlugField(max_length=50, unique=True, verbose_name="Código"),
        ),
    ]
