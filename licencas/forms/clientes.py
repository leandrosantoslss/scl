from django import forms

from licencas.models import Cliente
from licencas.validators import validate_document


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = (
            "nome",
            "cnpjcpf",
            "email",
            "telefone",
            "ativo",
            "cep",
            "endereco",
            "endnumero",
            "endbairro",
            "endcomplemento",
            "endUF",
            "endcidade",
            "endcodpais",
            "endpais",
        )

    def clean_cnpjcpf(self):
        return self.cleaned_data["cnpjcpf"]

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("bloqueado") and not (cleaned.get("motivo_bloqueio") or "").strip():
            self.add_error("motivo_bloqueio", "Informe o motivo do bloqueio.")
        return cleaned
