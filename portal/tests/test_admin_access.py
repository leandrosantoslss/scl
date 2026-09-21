import pytest
from django.contrib.auth import get_user_model


@pytest.mark.django_db
def test_staff_non_superuser_cannot_access_admin(client):
    user = get_user_model().objects.create_user("staff", password="secret", is_staff=True)
    client.force_login(user)
    assert client.get("/admin/").status_code in {302, 403}


@pytest.mark.django_db
def test_superuser_can_access_admin(client):
    user = get_user_model().objects.create_superuser("root", "root@example.com", "secret")
    client.force_login(user)
    assert client.get("/admin/").status_code == 200
