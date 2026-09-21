from datetime import timedelta

from django.db import IntegrityError, transaction
from dateutil.relativedelta import relativedelta

from financeiro.models import Cobranca, ConfiguracaoFinanceira


MONTHS = {"monthly": 1, "quarterly": 3, "semiannual": 6, "annual": 12}


def meses_por_periodicidade(periodicidade):
    return MONTHS[periodicidade]


def _configuracao():
    try:
        return ConfiguracaoFinanceira.objects.get(pk=1)
    except ConfiguracaoFinanceira.DoesNotExist:
        return ConfiguracaoFinanceira(dia_vencimento=5, dias_carencia=0)


def _carencia_efetiva(assinatura):
    if assinatura.dias_carencia is not None:
        return assinatura.dias_carencia
    return _configuracao().dias_carencia


def _carencia_snapshot(vencimento, dias_carencia):
    return vencimento + timedelta(days=int(dias_carencia))


def _defaults_para(assinatura, vencimento):
    return {
        "vencimento": vencimento,
        "fim_carencia": _carencia_snapshot(vencimento, _carencia_efetiva(assinatura)),
        "valor_original": assinatura.valor_recorrente,
        "status": Cobranca.Status.ABERTA,
        "origem": "scl",
    }


def _obter_ou_criar(assinatura, vencimento):
    try:
        with transaction.atomic():
            return Cobranca.objects.get_or_create(
                assinatura=assinatura,
                competencia=vencimento,
                defaults=_defaults_para(assinatura, vencimento),
            )
    except IntegrityError:
        # Concorrente inseriu a mesma competência: devolve a linha existente.
        return Cobranca.objects.get(assinatura=assinatura, competencia=vencimento), False


@transaction.atomic
def gerar_cobrancas_assinatura(assinatura, *, ate):
    """Gera o cronograma a partir do primeiro vencimento até `ate`.

    - Assinatura ativa com término: gera até a data final.
    - Assinatura sem término: mantém pelo menos a próxima cobrança.
    - Assinatura inativa: nada a gerar.
    - Assinatura com origem de cobrança externa não é processada (Plan 05).
    """
    if not assinatura.ativo:
        return []
    if _origem_externa(assinatura):
        return []

    charge_criadas = []
    vencimento = assinatura.primeiro_vencimento
    avanco = relativedelta(months=meses_por_periodicidade(assinatura.periodicidade))

    while vencimento <= ate:
        if assinatura.data_fim and vencimento > assinatura.data_fim:
            break
        cobranca, criada = _obter_ou_criar(assinatura, vencimento)
        if criada:
            charge_criadas.append(cobranca)
        vencimento = vencimento + avanco
    return charge_criadas


def _origem_externa(assinatura):
    """Assinaturas sob origem legada recebem cobranças apenas pela API."""
    try:
        return assinatura.origem_cobranca is not None
    except Exception:
        return False
