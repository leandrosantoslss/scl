from datetime import date


def _dv(digits):
    base = list(map(int, digits))
    weight = len(base) + 1
    total = sum(value * (weight - index) for index, value in enumerate(base))
    remainder = total % 11
    dv = 11 - remainder
    return 0 if dv >= 10 else dv


def gerar_cpf(seed: int) -> str:
    nine = f"{seed % 999999999:09d}"
    d1 = _dv(nine)
    d2 = _dv(nine + str(d1))
    return nine + str(d1) + str(d2)


def cliente_kwargs(nome, documento, **extra):
    values = {
        "nome": nome,
        "cnpjcpf": documento,
        "email": "a@b.com",
        "telefone": "1",
        "cep": "1",
        "endereco": "Rua",
        "endnumero": "1",
        "endbairro": "B",
        "endcomplemento": "-",
        "endUF": "SP",
        "endcidade": "S",
        "endcodpais": 55,
        "endpais": "Brasil",
    }
    values.update(extra)
    return values


def data_comercial():
    return {
        "valor_recorrente": "10.00",
        "periodicidade": "monthly",
        "data_inicio": date(2026, 1, 1),
        "primeiro_vencimento": date(2026, 1, 5),
    }
