import io

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from licencas.models import Cliente, ClienteSistema, Sistema


def _cliente(nome, cnpjcpf):
    return Cliente.objects.create(
        nome=nome, cnpjcpf=cnpjcpf, email="a@b.com", telefone="1", cep="1",
        endereco="R", endnumero="1", endbairro="B", endcomplemento="-",
        endUF="SP", endcidade="S", endcodpais=55, endpais="Brasil",
    )


@pytest.mark.django_db
def test_audit_command_passes_on_clean_data():
    _cliente("Acme", "12345678000195")

    buffer = io.StringIO()
    call_command("audit_legacy_data", stdout=buffer)
    text = buffer.getvalue()
    assert "invalid_documents=0" in text
    assert "duplicate_documents=0" in text
    assert "duplicate_client_system_pairs=0" in text


@pytest.mark.django_db
def test_audit_command_detects_invalid_document():
    _cliente("Ruim", "11111111111")

    buffer = io.StringIO()
    with pytest.raises(CommandError):
        call_command("audit_legacy_data", stdout=buffer, stderr=buffer)

    text = buffer.getvalue()
    assert "invalid_documents=1" in text


@pytest.mark.django_db
def test_duplicate_documents_are_now_blocked_by_schema():
    from django.db import IntegrityError

    _cliente("Original", "12345678000195")
    with pytest.raises(IntegrityError):
        _cliente("Duplicado", "12345678000195")


@pytest.mark.django_db
def test_duplicate_pairs_are_now_blocked_by_schema():
    from django.db import IntegrityError

    cliente = _cliente("Acme", "12345678000195")
    sistema = Sistema.objects.create(nome="ERP")
    fields = dict(
        valor_recorrente="10.00",
        periodicidade="monthly",
        data_inicio="2026-01-01",
        primeiro_vencimento="2026-01-05",
    )
    ClienteSistema.objects.create(cliente=cliente, sistema=sistema, **fields)
    with pytest.raises(IntegrityError):
        ClienteSistema.objects.create(cliente=cliente, sistema=sistema, **fields)
