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
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["codigo"].disabled = True
