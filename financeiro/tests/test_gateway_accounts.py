import pytest
from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from financeiro.crypto import decrypt_config
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
