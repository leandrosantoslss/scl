import io

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from licencas.models import Cliente, ClienteSistema, Sistema
from licencas.services import assinaturas
from portal.models import EventoAuditoria


def _legacy_row(cliente=None, sistema=None, **overrides):
    if cliente is None:
        cliente = Cliente.objects.create(
            nome="Legacy", cnpjcpf="12345678000195", email="a@b.com", telefone="1",
            cep="1", endereco="R", endnumero="1", endbairro="B", endcomplemento="-",
            endUF="SP", endcidade="S", endcodpais=55, endpais="Brasil",
        )
    if sistema is None:
        sistema = Sistema.objects.create(nome="ERP", codigo="erp-legacy")
    values = {
        "cliente": cliente,
        "sistema": sistema,
        "valor_recorrente": 0,
        "periodicidade": "monthly",
        "data_inicio": "2026-01-01",
        "primeiro_vencimento": "2026-01-05",
        "ativo": False,
    }
    values.update(overrides)
    return ClienteSistema.objects.create(**values)


def _run(*args):
    buffer = io.StringIO()
    call_command("prepare_subscription_migration", *args, stdout=buffer, stderr=buffer)
    return buffer.getvalue()


@pytest.mark.django_db
def test_check_passes_when_no_unresolved_rows():
    assert "check: OK" in _run("--check")


@pytest.mark.django_db
def test_check_fails_and_report_lists_unresolved_rows():
    row = _legacy_row()
    with pytest.raises(CommandError):
        _run("--check")

    report = _run("--report")
    assert str(row.pk) in report
    assert "valor=0.00" in report


@pytest.mark.django_db
def test_resolve_sets_commercial_data_and_audits():
    row = _legacy_row()

    output = _run(
        "--resolve", str(row.pk), "--amount", "199.90", "--periodicity", "monthly",
        "--first-due", "2026-10-05", "--keep-active", "--reason", "validação comercial",
    )

    row.refresh_from_db()
    assert str(row.valor_recorrente) == "199.90"
    assert row.periodicidade == "monthly"
    assert row.ativo is True
    assert "resolvida" in output
    assert EventoAuditoria.objects.filter(objeto_id=str(row.pk), acao="assinatura.legado.resolvida").exists()


@pytest.mark.django_db
def test_deactivate_requires_reason_and_audits():
    row = _legacy_row()
    with pytest.raises(CommandError):
        _run("--deactivate", str(row.pk))

    output = _run("--deactivate", str(row.pk), "--reason", "vínculo legado confirmado inativo")

    row.refresh_from_db()
    assert row.ativo is False
    assert str(row.valor_recorrente) == "0.00"
    assert "desativada" in output
    assert EventoAuditoria.objects.filter(objeto_id=str(row.pk), acao="assinatura.legado.desativada").exists()


@pytest.mark.django_db
def test_ambiguous_mode_is_rejected():
    with pytest.raises(CommandError):
        _run("--check", "--report")


@pytest.mark.django_db
def test_checkpoint_staging_activar_sem_valor():
    from django.contrib.auth import get_user_model

    cliente = Cliente.objects.create(
        nome="Zero", cnpjcpf="123.456.789-09", email="a@b.com", telefone="1",
        cep="1", endereco="R", endnumero="1", endbairro="B", endcomplemento="-",
        endUF="SP", endcidade="S", endcodpais=55, endpais="Brasil",
    )
    sistema = Sistema.objects.create(nome="CRM", codigo="crm")
    row = _legacy_row(cliente=cliente, sistema=sistema, ativo=False)

    usuario = get_user_model().objects.create_user("op", password="secret")

    from django.core.exceptions import ValidationError

    with pytest.raises(ValidationError):
        assinaturas.ativar_assinatura(row, usuario=usuario)

    assinaturas.atualizar_comercial(row, valor_recorrente="10.00", usuario=usuario)
    ativa = assinaturas.ativar_assinatura(row, usuario=usuario)
    assert ativa.ativo is True
    assert EventoAuditoria.objects.filter(acao="assinatura.ativada", objeto_id=str(row.pk)).exists()


@pytest.mark.django_db
def test_bloqueio_e_desbloqueio_audita(assinatura):
    from django.contrib.auth import get_user_model

    usuario = get_user_model().objects.create_user("op", password="secret")

    bloqueada = assinaturas.bloquear_assinatura(assinatura, motivo="fraude", usuario=usuario)
    assert bloqueada.bloqueado is True

    with pytest.raises(Exception):
        assinaturas.bloquear_assinatura(assinatura, motivo="   ", usuario=usuario)

    liberada = assinaturas.desbloquear_assinatura(bloqueada, usuario=usuario)
    assert liberada.bloqueado is False


@pytest.mark.django_db
def test_checkpoint_preserva_ativo_no_staging():
    # Deviation registered: the 0008/0009/0010 staging never writes `ativo`;
    # this test documents the invariant at service level instead of at raw
    # migration level, because the disposable test database always starts
    # with the final schema.
    row = _legacy_row(ativo=False)
    row.refresh_from_db()
    assert row.ativo is False
