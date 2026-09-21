def test_production_settings_have_nosniff_and_referrer():
    from django.conf import settings

    assert settings.SECURE_CONTENT_TYPE_NOSNIFF is True
    assert settings.SECURE_REFERRER_POLICY is not None
    assert settings.SESSION_COOKIE_HTTPONLY is True
    assert settings.SESSION_COOKIE_SAMESITE in {"Lax", "Strict"}
    assert not settings.DEBUG
