from datetime import datetime

from django import forms

from financeiro.models import ConfiguracaoFinanceira, Cobranca, Pagamento, ContaGateway



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


class ContaGatewayForm(WidgetBase):
    """Formulário de Conta de Gateway com campos individuais para credenciais.

    As credenciais são enviadas de forma segregada, validadas campo a campo
    pelo Django, e depois encryptadas com Fernet e gravadas em
    `conta.configuracao_criptografada` como um JSON único.
    """

    client_id = forms.CharField(
        max_length=255,
        required=False,
        label="Client ID",
        help_text="Identificador público do provedor (Efí, Sicredi ou Sicoob).",
    )
    client_secret = forms.CharField(
        max_length=512,
        required=False,
        label="Client Secret",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Segredo usado para autenticação OAuth2. Nunca fica em texto clara.",
    )
    pix_key = forms.CharField(
        max_length=255,
        required=False,
        label="Chave PIX",
        help_text="Chave PIX da empresa para emissor cobrança PIX.",
    )
    certificado_digital_base64 = forms.CharField(
        required=False,
        label="Certificado Digital (Base 64)",
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Cole o conteúdo do certificado digital codificado em Base 64 (PEM).",
    )
    certificado_digital_senha = forms.CharField(
        max_length=255,
        required=False,
        label="Senha do Certificado Digital",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Senha para abrir o certificado digital (mTLS).",
    )

    class Meta:
        model = ContaGateway
        fields = ("nome", "provedor", "ambiente", "habilita_boleto", "habilita_pix")

    def configs_do_container(self):
        """Retorna o dict de configuração coletado pelos campos individuais."""
        return {
            "client_id": (self.cleaned_data.get("client_id") or "").strip(),
            "client_secret": (self.cleaned_data.get("client_secret") or "").strip(),
            "pix_key": (self.cleaned_data.get("pix_key") or "").strip(),
            "certificate_path": "inlineorary-excluded",
            "certificate_base64": (self.cleaned_data.get("certificado_digital_base64") or "").strip(),
            "certificate_password": (self.cleaned_data.get("certificado_digital_senha") or "").strip(),
        }
