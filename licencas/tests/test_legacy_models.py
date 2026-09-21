import pytest

from licencas.models import AcessoMaquina, Cliente, ClienteSistema, Sistema


def _cliente(nome="Acme", cnpjcpf="12345678000195"):
    return Cliente.objects.create(
        nome=nome, cnpjcpf=cnpjcpf, email="a@b.com", telefone="1", cep="1",
        endereco="Rua", endnumero="1", endbairro="B", endcomplemento="-",
        endUF="SP", endcidade="S", endcodpais=55, endpais="Brasil",
    )


@pytest.mark.django_db
def test_cliente_sistema_string_contains_both_names():
    cliente = _cliente()
    sistema = Sistema.objects.create(nome="ERP", codigo="erp")
    vinculo = ClienteSistema.objects.create(
        cliente=cliente,
        sistema=sistema,
        valor_recorrente="10.00",
        periodicidade="monthly",
        data_inicio="2026-01-01",
        primeiro_vencimento="2026-01-05",
    )
    assert str(vinculo) == "Acme - ERP"


@pytest.mark.django_db
def test_acesso_string_is_text():
    acesso = AcessoMaquina(cliente=10, sistema=20)
    assert str(acesso) == "Cliente 10 - Sistema 20"
