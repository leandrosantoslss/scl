import json

from cryptography.fernet import Fernet, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def _fernet():
    keys = getattr(settings, "SCL_CONFIG_ENCRYPTION_KEYS", None)
    if not keys:
        raise ImproperlyConfigured("SCL_CONFIG_ENCRYPTION_KEYS é obrigatório")
    return MultiFernet([Fernet(key.encode()) for key in keys])


def encrypt_config(config):
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"))
    return _fernet().encrypt(canonical.encode()).decode()


def decrypt_config(ciphertext):
    payload = _fernet().decrypt(ciphertext.encode()).decode()
    return json.loads(payload)
