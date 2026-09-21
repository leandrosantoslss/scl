from datetime import date
from itertools import count

import pytest

from licencas.models import Cliente, ClienteSistema
from licencas.tests.helpers import cliente_kwargs, gerar_cpf


@pytest.fixture
def cliente_payload():
    seq = count(400)
    values = cliente_kwargs(
        "Empresa Exemplo",
        gerar_cpf(next(seq) % 999999999),
        email="financeiro@example.com",
        telefone="11999999999",
    )
    values.update({"cep": "01001000", "endereco": "Praça da Sé"})
    return values


@pytest.fixture
def assinatura_factory(db):
    documents = count(100000001)

    def factory(**overrides):
        cliente = Cliente.objects.create(
            nome="Empresa Exemplo",
            cnpjcpf=str(gerar_cpf(next(documents) % 999999999)),
            email="financeiro@example.com",
            telefone="11999999999",
            cep="01001000",
            endereco="Praça da Sé",
            endnumero="1",
            endbairro="Sé",
            endcomplemento="Sala 1",
            endUF="SP",
            endcidade="São Paulo",
            endcodpais=55,
            endpais="Brasil",
        )
        from licencas.models import Sistema

        sistema = Sistema.objects.create(nome="ERP", codigo=f"erp-{next(documents) % 999999}")
        values = {
            "cliente": cliente,
            "sistema": sistema,
            "valor_recorrente": "199.90",
            "periodicidade": "monthly",
            "data_inicio": date(2026, 1, 1),
            "primeiro_vencimento": date(2026, 1, 5),
        }
        values.update(overrides)
        return ClienteSistema.objects.create(**values)
    return factory


@pytest.fixture
def assinatura(assinatura_factory):
    return assinatura_factory()


@pytest.fixture
def cobranca_payload():
    return {
        "competencia": date(2026, 1, 1),
        "vencimento": date(2026, 1, 5),
        "fim_carencia": date(2026, 1, 10),
        "valor_original": "199.90",
    }


@pytest.fixture
def vencida_basica(assinatura_factory):
    assinatura = assinatura_factory(dia_vencimento=5)
    cobranca = Cobranca.objects.create(
        assinatura=assinatura,
        competencia=date(2026, 1, 1),
        vencimento=date(2026, 1, 5),
        fim_carencia=date(2026, 1, 10),
        valor_original="100.00",
    )
    return assinatura, cobranca


from financeiro.models import Cobranca  # noqa: E402

