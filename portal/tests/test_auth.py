import re

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse


def test_anonymous_portal_redirects_to_login(client):
    response = client.get(reverse("portal:home"))
    assert response.status_code == 302
    assert reverse("login") in response["Location"]


@pytest.mark.django_db
def test_authenticated_user_opens_portal(client):
    user = get_user_model().objects.create_user("operator", password="secret")
    client.force_login(user)
    assert client.get(reverse("portal:home")).status_code == 200


@pytest.mark.django_db
def test_logout_requires_post(client):
    user = get_user_model().objects.create_user("operator", password="secret")
    client.force_login(user)
    assert client.get(reverse("logout")).status_code == 405
    assert client.post(reverse("logout")).status_code == 302


@pytest.mark.django_db
def test_logout_without_csrf_token_is_rejected(csrf_client):
    user = get_user_model().objects.create_user("operator", password="secret")
    csrf_client.force_login(user)
    response = csrf_client.post(reverse("logout"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_logout_with_valid_csrf_token_succeeds(csrf_client):
    user = get_user_model().objects.create_user("operator", password="secret")
    csrf_client.force_login(user)
    home = csrf_client.get(reverse("portal:home"))
    match = re.search(
       'name="csrfmiddlewaretoken" value="([^"]+)"', home.content.decode()
    )
    assert match is not None
    response = csrf_client.post(
        reverse("logout"), data={"csrfmiddlewaretoken": match.group(1)}
    )
    assert response.status_code == 302
