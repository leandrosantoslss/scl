from django import forms

from integracoes.models import IntegracaoLegado


class IntegracaoForm(forms.ModelForm):
    escopos_texto = forms.CharField(
        required=False,
        label="Escopos (um por linha)",
        widget=forms.Textarea(attrs={"rows": 5}),
    )

    class Meta:
        model = IntegracaoLegado
        fields = ("nome",)
