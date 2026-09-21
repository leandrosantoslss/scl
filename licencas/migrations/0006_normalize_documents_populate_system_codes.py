from django.db import migrations
from django.utils.text import slugify


def normalize_documents_and_populate_system_codes(apps, schema_editor):
    Cliente = apps.get_model("licencas", "Cliente")
    Sistema = apps.get_model("licencas", "Sistema")

    seen_documents = {}
    collision_ids = []
    for cliente in Cliente.objects.all().order_by("id"):
        normalized = "".join(c for c in cliente.cnpjcpf or "" if c.isdigit())
        if normalized in seen_documents:
            collision_ids.append((seen_documents[normalized], cliente.id))
        else:
            seen_documents[normalized] = cliente.id
            if cliente.cnpjcpf != normalized:
                cliente.cnpjcpf = normalized
                cliente.save()

    if collision_ids:
        raise RuntimeError(
            "Colisão de documentos normalizados na migração 0006; "
            f"pares de IDs de linha: {collision_ids}"
        )

    seen_codes = set(Sistema.objects.exclude(codigo__isnull=True).values_list("codigo", flat=True))
    for sistema in Sistema.objects.all().order_by("id"):
        if sistema.codigo:
            seen_codes.add(sistema.codigo)
            continue
        base_code = slugify(sistema.nome) or f"sistema-{sistema.id}"
        code = base_code
        if code in seen_codes:
            code = f"{base_code}-{sistema.id}"
        counter = 2
        while code in seen_codes:
            code = f"{base_code}-{sistema.id}-{counter}"
            counter += 1
        seen_codes.add(code)
        sistema.codigo = code
        sistema.save()


def revert(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("licencas", "0005_cliente_bloqueado_cliente_bloqueado_em_and_more"),
    ]

    operations = [
        migrations.RunPython(normalize_documents_and_populate_system_codes, revert),
    ]
