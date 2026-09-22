from datetime import datetime

from django import forms

from financeiro.models import ConfiguracaoFinanceira, Cobranca, Pagamento



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


class PagamentoManualForm(WidgetBase):
    class Meta:
        model = Pagamento
        fields = ("valor", "forma", "pago_em")
        widgets = {"pago_em": forms.DateTimeInput(attrs={"type": "datetime-local"})}

    def clean_valor(self):
        from decimal import Decimal

        valor = Decimal(str(self.cleaned_data["valor"]))
        if valor <= 0:
            raise forms.ValidationError("Precisa ser um valor positivo.")
        return valor


class MotivoForm(forms.Form):
    motivo = forms.CharField(
        label="Motivo",
        widget=forms.Textarea(attrs={"rows": 3}),
        max_length=500,
    )

    def clean_motivo(self):
        texto = (self.cleaned_data["motivo"] or "").strip()
        if not texto:
            raise forms.ValidationError("Informe o motivo.")
        return texto


class ConfiguracaoForm(WidgetBase):
    motivo = forms.CharField(required=False, max_length=255)

    class Meta:
        model = ConfiguracaoFinanceira
        fields = ("dia_vencimento", "dias_carencia", "timezone")

    def clean_dia_vencimento(self):
        dia = self.cleaned_data["dia_vencimento"]
        if not (1 <= dia <= 28):
            raise forms.ValidationError("Use um dia entre 1 e 28.")
        return dia

    def clean_dias_carencia(self):
        carência = self.cleaned_data["dias_carencia"]
        if carência < 0:
            raise forms.ValidationError("A carência não pode ser negativa.")
        return carência
