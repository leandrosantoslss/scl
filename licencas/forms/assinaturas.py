from django import forms

from licencas.models import ClienteSistema


class AssinaturaForm(forms.ModelForm):
    class Meta:
        model = ClienteSistema
        fields = (
            "cliente",
            "sistema",
            "valor_recorrente",
            "periodicidade",
            "data_inicio",
            "data_fim",
            "primeiro_vencimento",
            "dia_vencimento",
            "dias_carencia",
        )
        widgets = {
            "data_inicio": forms.DateInput(attrs={"type": "date"}),
            "data_fim": forms.DateInput(attrs={"type": "date"}),
            "primeiro_vencimento": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            # Sugestão provisória: dia 5 até ConfiguracaoFinanceira existir (Plan 04).
            self.fields["primeiro_vencimento"].initial = None

    def clean(self):
        from datetime import date

        cleaned = super().clean()
        first = cleaned.get("primeiro_vencimento")
        if first is None and self.initial is not None:
            pass
        if not cleaned.get("data_fim"):
            cleaned["data_fim"] = None
        return cleaned

    def sugerir_primeiro_vencimento(self, data_inicio):
        if data_inicio is None:
            return None
        if data_inicio.day <= 5:
            return data_inicio.replace(day=5)
        if data_inicio.month == 12:
            return data_inicio.replace(year=data_inicio.year + 1, month=1, day=5)
        return data_inicio.replace(month=data_inicio.month + 1, day=5)
