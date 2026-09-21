from django import forms

from licencas.models import Sistema


class SistemaForm(forms.ModelForm):
    class Meta:
        model = Sistema
        fields = ("nome", "codigo", "ativo", "descricao")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["codigo"].disabled = True
