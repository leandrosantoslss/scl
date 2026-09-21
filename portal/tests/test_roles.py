import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.http import HttpResponse
from django.test import RequestFactory

from portal.permissions import group_required
from portal.roles import ADMINISTRADOR, CADASTRO, CONSULTA, FINANCEIRO


@pytest.mark.django_db
def test_sync_roles_is_idempotent():
    call_command("sync_roles")
    call_command("sync_roles")
    assert set(Group.objects.values_list("name", flat=True)) >= {
        ADMINISTRADOR,
        CADASTRO,
        FINANCEIRO,
        CONSULTA,
    }


@pytest.mark.django_db
def test_sync_roles_applies_permission_prefixes():
    call_command("sync_roles")

    administrador = Group.objects.get(name=ADMINISTRADOR)
    codes = set(administrador.permissions.values_list("codename", flat=True))
    assert "view_cliente" in codes
    assert "add_cliente" in codes
    assert "change_cliente" in codes

    consulta = Group.objects.get(name=CONSULTA)
    consulta_codes = set(consulta.permissions.values_list("codename", flat=True))
    assert "view_cliente" in consulta_codes
    assert "add_cliente" not in consulta_codes


@pytest.mark.django_db
def test_group_required_allows_member():
    @group_required(CONSULTA)
    def protected(request):
        return HttpResponse("ok")

    viewer = get_user_model().objects.create_user("viewer", password="secret")
    Group.objects.get_or_create(name=CONSULTA)
    viewer.groups.add(Group.objects.get(name=CONSULTA))

    request = RequestFactory().get("/")
    request.user = viewer

    assert protected(request).content == b"ok"


@pytest.mark.django_db
def test_group_required_denies_non_member():
    @group_required(CONSULTA)
    def protected(request):
        return HttpResponse("ok")

    request = RequestFactory().get("/")
    request.user = get_user_model().objects.create_user("outsider", password="secret")

    with pytest.raises(PermissionDenied):
        protected(request)


@pytest.mark.django_db
def test_group_required_allows_superuser():
    @group_required(CONSULTA)
    def protected(request):
        return HttpResponse("ok")

    request = RequestFactory().get("/")
    request.user = get_user_model().objects.create_superuser("root", "root@example.com", "secret")

    assert protected(request).content == b"ok"
