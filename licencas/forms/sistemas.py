from django import forms

from licencas.models import Sistema



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


class SistemaForm(WidgetBase):
    class Meta:
        model = Sistema
        fields = ("nome", "codigo", "ativo", "descricao")

    def __init__(self, *args, **kwargs):
        from django.utils.text import slugify
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["codigo"].disabled = True

    def clean_codigo(self):
        """Codigo em branco → gera automaticamente slug(nome)+sufixo único."""
        from django.utils.text import slugify

        codigo = (self.cleaned_data.get("codigo") or "").strip()
        if codigo:
            return codigo

        base = slugify(self.cleaned_data.get("nome") or "") or "sistema"
        candidate = base
        counter = 2
        while (
            Sistema.objects.filter(codigo=candidate)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            candidate = f"{base}-{counter}"
            counter += 1
        # marca o widget para exibir o valor gerado
        self.fields["codigo"].widget.attrs["placeholder"] = candidate
        self.cleaned_data["codigo"] = candidate
        return candidate
