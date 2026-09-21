from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count

from licencas.models import Cliente, ClienteSistema
from licencas.validators import validate_document


class Command(BaseCommand):
    help = "Auditoria somente leitura dos dados legados (documentos e vínculos)."

    def handle(self, *args, **options):
        invalid_documents = 0
        for document in Cliente.objects.values_list("cnpjcpf", flat=True):
            try:
                validate_document(document)
            except Exception:
                invalid_documents += 1

        duplicate_documents = (
            Cliente.objects.values("cnpjcpf")
            .annotate(total=Count("id"))
            .filter(total__gt=1)
            .count()
        )

        duplicate_client_system_pairs = (
            ClienteSistema.objects.values("cliente_id", "sistema_id")
            .annotate(total=Count("id"))
            .filter(total__gt=1)
            .count()
        )

        self.stdout.write(f"invalid_documents={invalid_documents}")
        self.stdout.write(f"duplicate_documents={duplicate_documents}")
        self.stdout.write(f"duplicate_client_system_pairs={duplicate_client_system_pairs}")

        if invalid_documents or duplicate_documents or duplicate_client_system_pairs:
            raise CommandError("auditoria de dados legados encontrou problemas")
