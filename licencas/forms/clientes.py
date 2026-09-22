from django import forms

from licencas.models import Cliente
from licencas.validators import validate_document



class WidgetBase(forms.ModelForm):
    """Aplica classes Bootstrap Duralux a todos os widgets do ModelForm."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget
            atual = widget.attrs.get("class", "")

            if isinstance(widget, forms.widgets.CheckboxInput):
                widget.attrs["class"] = ("form-check-input " + atual).strip()
            elif isinstance(widget, forms.widgets.Textarea):
                widget.attrs["class"] = ("form-control form-textarea " + atual).strip()
            elif isinstance(widget, forms.widgets.Select) or isinstance(widget, forms.widgets.SelectMultiple):
                widget.attrs["class"] = ("form-select " + atual).strip()
            else:
                widget.attrs["class"] = ("form-control " + atual).strip()


class ClienteForm(WidgetBase):
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
