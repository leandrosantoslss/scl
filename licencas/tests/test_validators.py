import pytest
from django.core.exceptions import ValidationError

from licencas.validators import normalize_document, validate_document


def test_normalize_document_removes_mask():
    assert normalize_document("12.345.678/0001-95") == "12345678000195"


def test_validate_document_accepts_valid_cnpj():
    validate_document("12.345.678/0001-95")


def test_validate_document_accepts_valid_cpf():
    validate_document("529.982.247-25")


def test_validate_document_rejects_invalid_value():
    with pytest.raises(ValidationError):
        validate_document("11111111111")
