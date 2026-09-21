from datetime import date

import pytest

from licencas.models import Cliente, ClienteSistema, Sistema


@pytest.fixture
def cliente_payload():
    return {
        "nome": "Empresa Exemplo",
        "email": "financeiro@example.com",
        "telefone": "11999999999",
        "cep": "01001000",
        "endereco": "Praça da Sé",
        "endnumero": "1",
        "endbairro": "Sé",
        "endcomplemento": "Sala 1",
        "endUF": "SP",
        "endcidade": "São Paulo",
        "endcodpais": 55,
        "endpais": "Brasil",
    }


@pytest.fixture
def assinatura(db, cliente_payload):
    cliente = Cliente.objects.create(**cliente_payload, cnpjcpf="12345678000195")
    sistema = Sistema.objects.create(nome="ERP", codigo="erp")
    return ClienteSistema.objects.create(
        cliente=cliente,
        sistema=sistema,
        valor_recorrente="199.90",
        periodicidade="monthly",
        data_inicio=date(2026, 1, 1),
        primeiro_vencimento=date(2026, 1, 5),
    )
