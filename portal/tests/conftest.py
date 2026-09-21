import pytest
from django.test import Client


@pytest.fixture
def csrf_client():
    return Client(enforce_csrf_checks=True)
