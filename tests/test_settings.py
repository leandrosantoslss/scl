import importlib

from django.conf import settings


def test_timezone_defaults_to_sao_paulo():
    assert settings.TIME_ZONE == "America/Sao_Paulo"


def test_secret_key_is_not_the_scaffold_value():
    assert "django-insecure-w98yc" not in settings.SECRET_KEY


def test_database_configuration_has_no_literal_password():
    source = importlib.import_module("app.settings").__file__
    assert "Lss167349" not in open(source, encoding="utf-8").read()
