from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError

from licencas.models import ClienteSistema

from financeiro.models import Cobranca
from financeiro.services.cobrancas import gerar_cobrancas_assinatura


class Command(BaseCommand):
    help = "Rotina idempotente diária de geração de cobranças (somente origem SCL)."

    def add_arguments(self, parser):
        parser.add_argument("--today", type=str, required=False)
        parser.add_argument("--lookahead-days", type=int, default=45)

    def handle(self, *args, **options):
        if options["today"]:
            year, month, day = (int(part) for part in options["today"].split("-"))
            hoje = date(year, month, day)
        else:
            from django.utils import timezone

            hoje = timezone.localdate()

        ate = hoje + timedelta(days=options["lookahead_days"])

        subscriptions_scanned = 0
        charges_created = 0
        charges_existing = 0
        subscriptions_failed = 0

        for assinatura in ClienteSistema.objects.filter(ativo=True).order_by("pk"):
            subscriptions_scanned += 1
            existing_before = Cobranca.objects.filter(assinatura=assinatura).count()
            try:
                gerar_cobrancas_assinatura(assinatura, ate=ate)
            except Exception:
                subscriptions_failed += 1
                continue
            total_after = Cobranca.objects.filter(assinatura=assinatura).count()
            charges_created += total_after - existing_before
            charges_existing += existing_before

        self.stdout.write(f"subscriptions_scanned={subscriptions_scanned}")
        self.stdout.write(f"charges_created={charges_created}")
        self.stdout.write(f"charges_existing={charges_existing}")
        self.stdout.write(f"subscriptions_failed={subscriptions_failed}")

        if subscriptions_failed:
            raise CommandError("gerar_cobrancas completou com falhas")
