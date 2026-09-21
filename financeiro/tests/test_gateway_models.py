from datetime import date

import pytest
from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import IntegrityError

from financeiro.crypto import decrypt_config, encrypt_config
from financeiro.models import Cobranca, ContaGateway, EmissaoCobranca, EventoGateway, Pagamento


@pytest.fixture
def encryption_keys(settings):
    keys = [Fernet.generate_key().decode()]
    settings.SCL_CONFIG_ENCRYPTION_KEYS = keys
    return keys


@pytest.mark.django_db
def test_encrypted_configuration_does_not_contain_secret(encryption_keys):
    ciphertext = encrypt_config({"client_secret": "super-secret"})
    assert "super-secret" not in ciphertext
    assert decrypt_config(ciphertext)["client_secret"] == "super-secret"


@pytest.mark.django_db
def test_encrypt_requires_keys(settings):
    settings.SCL_CONFIG_ENCRYPTION_KEYS = []
    from django.test import override_settings

    from financeiro import crypto

    with pytest.raises(ImproperlyConfigured):
        crypto._fernet()


@pytest.mark.django_db
def test_multiple_accounts_for_one_provider_are_allowed(encryption_keys, db):
    ContaGateway.objects.create(nome="Conta A", provedor="efi", habilita_pix=True, configuracao_criptografada="x")
    ContaGateway.objects.create(nome="Conta B", provedor="efi", habilita_pix=True, configuracao_criptografada="y")
    assert ContaGateway.objects.filter(provedor="efi").count() == 2


@pytest.mark.django_db
def test_only_one_active_emission_per_charge(encryption_keys, assinatura, cobranca_payload, db):
    from django.db import transaction

    cobranca = Cobranca.objects.create(assinatura=assinatura, **cobranca_payload)
    conta = ContaGateway.objects.create(nome="C1", provedor="efi", habilita_pix=True)

    EmissaoCobranca.objects.create(
        cobranca=cobranca, conta=conta, meio="pix", chave_idempotencia="k1"
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            EmissaoCobranca.objects.create(
                cobranca=cobranca, conta=conta, meio="pix", chave_idempotencia="k2"
            )


@pytest.mark.django_db
def test_external_event_id_only_unique_within_provider(encryption_keys, db):
    from django.db import transaction

    conta1 = ContaGateway.objects.create(nome="A", provedor="efi", habilita_pix=True)
    conta2 = ContaGateway.objects.create(nome="B", provedor="efi", habilita_pix=True)

    EventoGateway.objects.create(conta=conta1, provedor="efi", id_evento_externo="ev-1", tipo="paid", payload_hash="h")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            EventoGateway.objects.create(conta=conta2, provedor="efi", id_evento_externo="ev-1", tipo="paid", payload_hash="h2")
    EventoGateway.objects.create(conta=conta2, provedor="sicredi", id_evento_externo="ev-1", tipo="paid", payload_hash="h3")


@pytest.mark.django_db
def test_gateway_payment_requires_provenance(vencida_basica, encryption_keys):
    _assinatura, cobranca = vencida_basica
    provedor = "efi"

    with pytest.raises(Exception):
        Pagamento.objects.create(
            cobranca=cobranca,
            valor="10.00",
            pago_em=date(2026, 1, 5),
            forma="pix",
            origem="gateway",
            status="confirmed",
        )
