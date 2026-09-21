from datetime import date

from django.db import migrations


def _proximo_dia_cinco(data_inicio):
    """Próximo dia 5 emData igual ou após a data de início."""
    candidato = data_inicio.replace(day=min(5, 28))
    if candidato < data_inicio:
        import calendar
        ano, mes = data_inicio.year, data_inicio.month
        if mes == 12:
            ano, mes = ano + 1, 1
        else:
            mes += 1
        candidato = date(ano, mes, 5)
    if candidato < data_inicio:
        candidato = date(data_inicio.year, data_inicio.month, min(5, 28))
    return candidato


def derivar_dados_comerciais(apps, schema_editor):
    ClienteSistema = apps.get_model("licencas", "ClienteSistema")
    for assinatura in ClienteSistema.objects.all().order_by("id"):
        updates = {}
        if not assinatura.periodicidade:
            updates["periodicidade"] = "monthly"
        if not assinatura.data_inicio and assinatura.criado_em:
            updates["data_inicio"] = assinatura.criado_em.date()
        if not assinatura.primeiro_vencimento and assinatura.data_inicio:
            updates["primeiro_vencimento"] = _proximo_dia_cinco(assinatura.data_inicio)
        if updates:
            ClienteSistema.objects.filter(pk=assinatura.pk).update(**updates)


def revert(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("licencas", "0008_subscription_nullable_schema"),
    ]

    operations = [
        migrations.RunPython(derivar_dados_comerciais, revert),
    ]
