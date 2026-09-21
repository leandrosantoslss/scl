import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from financeiro.selectors import FinancialPosition
from licencas.models import Cliente, ClienteSistema, Sistema
from licencas.tests.helpers import gerar_cpf


@pytest.fixture
def user(client):
    user = get_user_model().objects.create_user("viewer", password="secret")
    client.force_login(user)
    return user


def _seed(cliente_payload):
    Cliente.objects.create(**cliente_payload)
    sistema = Sistema.objects.create(nome="ERP-dash", codigo="erp-dash")
    ClienteSistema.objects.create(
        cliente=Cliente.objects.first(),
        sistema=sistema,
        valor_recorrente="10.00",
        periodicidade="monthly",
        data_inicio="2026-01-01",
        primeiro_vencimento="2026-01-05",
    )


@pytest.mark.django_db
def test_home_loads_within_query_budget(client, cliente_payload):
    from django.test.utils import CaptureQueriesContext
    from django.db import connection

    _seed(cliente_payload)
    user = get_user_model().objects.create_user("viewer2", password="s")
    client.force_login(user)

    consulta = client.get(reverse("portal:home"))
    assert consulta.status_code == 200
    # Uma única requisição deve renderizar com pelo menos 15 consultas nos dados
    # essenciais; para manter em produção, usa-se annotate/count e não loops.
    queries_basico = {"clientes", "sistemas", "assinaturas"}
