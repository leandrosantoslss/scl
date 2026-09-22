import base64

import pytest
from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from financeiro.crypto import decrypt_config
from financeiro.forms import ContaGatewayForm
from financeiro.models import ContaGateway, EventoGateway, Pagamento  # noqa: F401
from financeiro.services import contas_gateway
from portal.models import EventoAuditoria


@pytest.fixture
def encryption_keys(settings):
    settings.SCL_CONFIG_ENCRYPTION_KEYS = [Fernet.generate_key().decode()]


@pytest.fixture
def conta_efi(db):
    return ContaGateway.objects.create(nome="Efí Principal", provedor="efi", habilita_pix=True)


@pytest.mark.django_db
def test_salvar_credenciais_criptografia_gera_auditoria(encryption_keys, conta_efi):
    usuario = get_user_model().objects.create_user("adm", password="s")
    contas_gateway.salvar_credenciais(
        conta=conta_efi,
        configuracao={"client_id": "client-x", "client_secret": "super-secret"},
        usuario=usuario,
    )

    conta_efi.refresh_from_db()
    assert "super-secret" not in conta_efi.configuracao_criptografada
    decodificado = decrypt_config(conta_efi.configuracao_criptografada)
    assert decodificado["client_secret"] == "super-secret"

    evento = EventoAuditoria.objects.get(acao="conta_gateway.credenciais.salvas")
    conteudo = str(evento.depois)
    assert "super-secret" not in conteudo
    assert "client_secret:" not in conteudo.lower()
    assert "client_id" in conteudo


@pytest.mark.django_db
def test_salvar_credenciais_rejeita_chaves_ausentes(encryption_keys, conta_efi):
    usuario = get_user_model().objects.create_user("adm", password="s")
    with pytest.raises(ValidationError):
        contas_gateway.salvar_credenciais(conta=conta_efi, configuracao={"client_id": "x"}, usuario=usuario)
    assert conta_efi.configuracao_criptografada == ""


@pytest.mark.django_db
def test_ativar_e_desativar_audita(encryption_keys, conta_efi):
    usuario = get_user_model().objects.create_user("adm", password="s")

    contas_gateway.desativar_conta(conta=conta_efi, usuario=usuario, motivo="suspeita")
    conta_efi.refresh_from_db()
    assert conta_efi.ativo is False
    assert EventoAuditoria.objects.filter(acao="conta_gateway.desativada", objeto_id=str(conta_efi.public_id)).exists()

    contas_gateway.ativar_conta(conta=conta_efi, usuario=usuario)
    conta_efi.refresh_from_db()
    assert conta_efi.ativo is True
    assert EventoAuditoria.objects.filter(acao="conta_gateway.ativada", objeto_id=str(conta_efi.public_id)).exists()


def test_form_converte_certificado_pfx_para_base64():
    certificado = b"certificado-pfx-de-teste"
    form = ContaGatewayForm(
        data={
            "nome": "Efí Sandbox",
            "provedor": "efi",
            "ambiente": "sandbox",
            "habilita_pix": "on",
            "client_id": "client-id",
            "client_secret": "client-secret",
            "api_key": "api-key",
            "certificado_digital_senha": "senha-certificado",
        },
        files={
            "certificado_pfx": SimpleUploadedFile(
                "certificado.pfx", certificado, content_type="application/x-pkcs12"
            )
        },
    )

    assert form.is_valid(), form.errors
    configuracao = form.configuracao_credenciais()

    assert configuracao["api_key"] == "api-key"
    assert configuracao["certificate_base64"] == base64.b64encode(certificado).decode("ascii")
    assert configuracao["certificate_password"] == "senha-certificado"


def test_form_rejeita_certificado_com_extensao_invalida():
    form = ContaGatewayForm(
        data={
            "nome": "Efí Sandbox",
            "provedor": "efi",
            "ambiente": "sandbox",
            "habilita_pix": "on",
            "client_id": "client-id",
            "client_secret": "client-secret",
        },
        files={
            "certificado_pfx": SimpleUploadedFile(
                "certificado.txt", b"nao-e-pfx", content_type="text/plain"
            )
        },
    )

    assert not form.is_valid()
    assert "certificado_pfx" in form.errors


@pytest.mark.django_db
def test_gateway_create_persiste_certificado_criptografado(encryption_keys, client):
    usuario = get_user_model().objects.create_superuser("adm", "adm@example.com", "s")
    client.force_login(usuario)
    certificado = b"certificado-pfx-de-teste"

    response = client.post(
        reverse("financeiro:gateway-create"),
        data={
            "nome": "Efí Sandbox",
            "provedor": "efi",
            "ambiente": "sandbox",
            "habilita_pix": "on",
            "client_id": "client-id",
            "client_secret": "client-secret",
            "api_key": "api-key",
            "certificado_digital_senha": "senha-certificado",
            "certificado_pfx": SimpleUploadedFile("certificado.pfx", certificado),
        },
    )

    assert response.status_code == 302
    conta = ContaGateway.objects.get(nome="Efí Sandbox")
    configuracao = decrypt_config(conta.configuracao_criptografada)
    assert configuracao["certificate_base64"] == base64.b64encode(certificado).decode("ascii")
    assert configuracao["certificate_password"] == "senha-certificado"
    assert "certificado-pfx-de-teste" not in conta.configuracao_criptografada
