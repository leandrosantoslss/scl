from django.core.exceptions import ValidationError
from django.db import transaction

from financeiro.models import ConfiguracaoFinanceira
from portal.audit import registrar_evento_auditoria


@transaction.atomic
def alterar_configuracao_financeira(*, values, usuario, motivo):
    locked = ConfiguracaoFinanceira.objects.select_for_update().filter(pk=1).first()
    if locked is None:
        locked = ConfiguracaoFinanceira(dia_vencimento=5, dias_carencia=0)

    antes = {"dia_vencimento": locked.dia_vencimento, "dias_carencia": locked.dias_carencia}

    locked.dia_vencimento = values.get("dia_vencimento", locked.dia_vencimento)
    locked.dias_carencia = values.get("dias_carencia", locked.dias_carencia)
    locked.alterado_por = usuario
    locked.full_clean()
    locked.save()

    registrar_evento_auditoria(
        acao="configuracao_financeira.alterada",
        objeto_tipo="financeiro.ConfiguracaoFinanceira",
        objeto_id="1",
        antes=antes,
        depois={"dia_vencimento": locked.dia_vencimento, "dias_carencia": locked.dias_carencia},
        origem="portal",
        usuario=usuario,
        motivo=values.get("motivo"),
    )
    return locked


def dia_efetivo_assinatura(assinatura):
    """Dia de vencimento da assinatura ou o padrão global."""
    if assinatura.dia_vencimento is not None:
        return assinatura.dia_vencimento
    config = ConfiguracaoFinanceira.objects.filter().first()
    return config.dia_vencimento if config else 5
