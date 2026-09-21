import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from licencas.models import Cliente, Sistema


@pytest.mark.django_db
def test_cliente_normalizes_document_before_save(cliente_payload):
    cliente = Cliente(**cliente_payload, cnpjcpf="12.345.678/0001-95")
    cliente.full_clean()
    cliente.save()
    assert cliente.cnpjcpf == "12345678000195"


@pytest.mark.django_db
def test_cliente_normalizes_document_on_direct_save(cliente_payload):
    cliente = Cliente.objects.create(**cliente_payload, cnpjcpf="12.345.678/0001-95")
    cliente.refresh_from_db()
    assert cliente.cnpjcpf == "12345678000195"


@pytest.mark.django_db
def test_cliente_block_requires_reason(cliente_payload):
    cliente = Cliente(**cliente_payload, cnpjcpf="12345678000195", bloqueado=True)
    with pytest.raises(ValidationError):
        cliente.full_clean()


@pytest.mark.django_db
def test_cliente_document_must_be_valid(cliente_payload):
    cliente = Cliente(**cliente_payload, cnpjcpf="11111111111")
    with pytest.raises(ValidationError):
        cliente.full_clean()


@pytest.mark.django_db
def test_cliente_document_is_unique(cliente_payload):
    Cliente.objects.create(**cliente_payload, cnpjcpf="12345678000195")
    with pytest.raises(IntegrityError):
        Cliente.objects.create(**cliente_payload, cnpjcpf="12345678000195")


@pytest.mark.django_db
def test_sistema_code_is_unique():
    Sistema.objects.create(nome="ERP", codigo="erp")
    with pytest.raises(IntegrityError):
        Sistema.objects.create(nome="Outro", codigo="erp")
