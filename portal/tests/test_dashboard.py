import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from licencas.models import Cliente, ClienteSistema, Sistema


@pytest.mark.django_db
def test_dashboard_counters_exact_values(client):
    Cliente.objects.create(nome="Acme", cnpjcpf="12345678000195", email="a@b.com", telefone="1", cep="1", endereco="R", endnumero="1", endbairro="B", endcomplemento="-", endUF="SP", endcidade="S", endcodpais=55, endpais="Brasil")
    sistema = Sistema.objects.create(nome="ERP", codigo="erp")
    ClienteSistema.objects.create(
        cliente=Cliente.objects.first(),
        sistema=sistema,
        valor_recorrente="10.00",
        periodicidade="monthly",
        data_inicio="2026-01-01",
        primeiro_vencimento="2026-01-05",
    )

    user = get_user_model().objects.create_user("viewer", password="secret")
    client.force_login(user)

    response = client.get(reverse("portal:home"))
    assert response.status_code == 200
    assert response.context["clientes_total"] == 1
    assert response.context["sistemas_total"] == 1
    assert response.context["assinaturas_total"] == 1
