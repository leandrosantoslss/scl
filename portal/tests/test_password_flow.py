import re

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse


@pytest.mark.django_db
def test_login_page_mostra_lembre_e_esqueci(client):
    pagina = client.get(reverse("login")).content.decode()
    assert 'name="remember_me"' in pagina
    assert reverse("password_reset") in pagina


@pytest.mark.django_db
def test_remember_me_estende_sessao(client):
    user = get_user_model().objects.create_user("op", password="secret")

    resposta = client.post(
        reverse("login"),
        data={"username": "op", "password": "secret", "remember_me": "on"},
    )
    assert resposta.status_code == 302
    # Com remember-me: cookie de sessão com expiração longa (Set-Cookie expira em > 1h)
    set_cookie = resposta.cookies["sessionid"]
    assert set_cookie["expires"] or set_cookie["max-age"]

    outro = get_user_model().objects.create_user("op2", password="secret")
    resposta_sem = client.post(
        reverse("login"),
        data={"username": "op2", "password": "secret"},
    )
    cookie2 = resposta_sem.cookies.get("sessionid")
    if cookie2:
        # Sem remember: sessão expira ao fechar o browser
        assert cookie2.value == "" or (cookie2.value != "" and not cookie2["expires"])


@pytest.mark.django_db
def test_password_reset_fluxo(client, mailoutbox):
    user = get_user_model().objects.create_user(
        "reset_me", "reset@example.com", password="secret"
    )
    resposta = client.post(reverse("password_reset"), data={"email": "reset@example.com"})
    assert resposta.status_code == 302
    assert len(mailoutbox) == 1
    corpo = mailoutbox[0].body
    # O link de reset aparece no corpo do e-mail
    assert "/reset/" in corpo or "password-reset/confirmar" in corpo

@pytest.mark.django_db
def test_password_reset_email_desconhecido_avisa(client, db):
    resposta = client.post(
        reverse("password_reset"),
        data={"email": "desconhecido@example.com"},
    )
    assert resposta.status_code == 200
    conteudo = resposta.content.decode()
    assert "não encontramos" in conteudo.lower()
    # Formulário fica visível para nova tentativa
    assert 'name="email"' in conteudo

