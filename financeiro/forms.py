from datetime import datetime

from django import forms

from financeiro.models import ConfiguracaoFinanceira, Cobranca, Pagamento


class PagamentoManualForm(forms.ModelForm):
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


class ConfiguracaoForm(forms.ModelForm):
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
