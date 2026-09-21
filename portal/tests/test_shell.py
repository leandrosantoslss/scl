import os

import pytest
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.urls import reverse


def test_duralux_assets_are_discoverable():
    theme = os.path.join("vendor", "duralux", "css", "theme.min.css")
    common_init = os.path.join("vendor", "duralux", "js", "common-init.min.js")
    assert finders.find(theme)
    assert finders.find(common_init)


@pytest.mark.django_db
def test_portal_uses_accessible_application_shell(client):
    user = get_user_model().objects.create_user("viewer", password="secret")
    client.force_login(user)
    content = client.get(reverse("portal:home")).content.decode()
    assert 'aria-label="Navegação principal"' in content
    assert "nxl-container" in content
    assert "Dashboard" in content
    assert "/static/vendor/duralux/css/theme.min.css" in content
    assert "/static/js/portal.js" in content
