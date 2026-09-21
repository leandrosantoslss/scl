import pytest

from licencas.tests.helpers import cliente_kwargs, gerar_cpf


@pytest.fixture
def cliente_payload():
    from itertools import count

    seq = count(900)
    values = cliente_kwargs(
        "Empresa Exemplo",
        gerar_cpf(next(seq) % 999999999),
        email="financeiro@example.com",
        telefone="11999999999",
    )
    return values
