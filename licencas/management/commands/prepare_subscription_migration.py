from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from licencas.models import ClienteSistema
from portal.audit import registrar_evento_auditoria


class Command(BaseCommand):
    help = "Prepara vÃ­nculos legados para a migraÃ§Ã£o de assinaturas (report/resolve/deactivate/check)."

    def add_arguments(self, parser):
        parser.add_argument("--report", action="store_true")
        parser.add_argument("--resolve", type=int, metavar="ID")
        parser.add_argument("--deactivate", type=int, metavar="ID")
        parser.add_argument("--check", action="store_true")
        parser.add_argument("--amount", type=str)
        parser.add_argument("--periodicity", type=str, choices=ClienteSistema.Periodicidade.values)
        parser.add_argument("--first-due", type=str)
        parser.add_argument("--keep-active", action="store_true")
        parser.add_argument("--reason", type=str)

    def handle(self, *args, **options):
        modes = [options["report"], options["resolve"] is not None, options["deactivate"] is not None, options["check"]]
        if sum(bool(mode) for mode in modes) != 1:
            raise CommandError("Escolha exatamente um: --report, --resolve, --deactivate ou --check.")

        if options["report"]:
            for unresolved in self._unresolved():
                self.stdout.write(
                    f"{unresolved.pk}: cliente={unresolved.cliente_id} sistema={unresolved.sistema_id} "
                    f"ativo={unresolved.ativo} valor={unresolved.valor_recorrente}"
                )
            return

        if options["check"]:
            unresolved_ids = [row.pk for row in self._unresolved()]
            if unresolved_ids:
                raise CommandError(f"Linhas nÃ£o resolvidas: {unresolved_ids}")
            self.stdout.write("check: OK â€” nenhuma linha pendente.")
            return

        pk = options["resolve"] if options["resolve"] is not None else options["deactivate"]
        with transaction.atomic():
            row = ClienteSistema.objects.select_for_update().get(pk=pk)
            if options["resolve"]:
                self._resolve(row, options)
            else:
                self._deactivate(row, options.get("reason"))

    def _unresolved(self):
        from decimal import Decimal

        return (
            ClienteSistema.objects.filter(valor_recorrente=Decimal("0.00"))
            .order_by("id")
        )

    def _resolve(self, row, options):
        if not options["amount"]:
            raise CommandError("--resolve exige --amount.")
        if not options["reason"]:
            raise CommandError("--resolve exige --reason.")
        from decimal import Decimal

        amount = Decimal(options["amount"])
        if amount <= 0:
            raise CommandError("--amount deve ser positivo.")
        if options["first_due"]:
            from datetime import date

            year, month, day = (int(part) for part in options["first_due"].split("-"))
            first_due = date(year, month, day)
        else:
            first_due = row.primeiro_vencimento
        if first_due is None:
            raise CommandError("--resolve exige --first-due quando o vencimento estÃ¡ ausente.")

        row.valor_recorrente = amount
        if options["periodicity"]:
            row.periodicidade = options["periodicity"]
        row.primeiro_vencimento = first_due
        if options["keep_active"]:
            row.ativo = True
        row.full_clean()
        row.save()
        registrar_evento_auditoria(
            acao="assinatura.legado.resolvida",
            objeto_tipo="licencas.ClienteSistema",
            objeto_id=row.pk,
            origem="portal",
            motivo=options["reason"],
        )
        self.stdout.write(self.style.SUCCESS(f"linha {row.pk} resolvida"))

    def _deactivate(self, row, reason):
        if not (reason or "").strip():
            raise CommandError("--deactivate exige --reason.")
        row.ativo = False
        row.full_clean()
        row.save()
        registrar_evento_auditoria(
            acao="assinatura.legado.desativada",
            objeto_tipo="licencas.ClienteSistema",
            objeto_id=row.pk,
            origem="portal",
            motivo=reason,
        )
        self.stdout.write(self.style.SUCCESS(f"linha {row.pk} desativada com motivo registrado"))

