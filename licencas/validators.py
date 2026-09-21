import re

from django.core.exceptions import ValidationError
from stdnum.br import cnpj, cpf


def normalize_document(value):
    return re.sub(r"\D", "", value or "")


def validate_document(value):
    normalized = normalize_document(value)
    if len(normalized) not in (11, 14) or len(set(normalized)) == 1:
        raise ValidationError("Informe um CPF ou CNPJ válido.")
    checker = cpf if len(normalized) == 11 else cnpj
    if not checker.is_valid(normalized):
        raise ValidationError("Informe um CPF ou CNPJ válido.")
