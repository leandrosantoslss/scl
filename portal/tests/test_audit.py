import pytest
from django.core.exceptions import ValidationError

from portal.audit import REDACTED, registrar_evento_auditoria
from portal.models import EventoAuditoria


@pytest.mark.django_db
def test_auditoria_registra_evento_completo():
    evento = registrar_evento_auditoria(
        acao="cliente.criado",
        objeto_tipo="licencas.Cliente",
        objeto_id="1",
        antes=None,
        depois={"nome": "Acme"},
        origem="portal",
    )
    assert evento.public_id
    assert evento.acao == "cliente.criado"
    assert evento.depois["nome"] == "Acme"


@pytest.mark.parametrize("campo", ["token", "client_secret", "authorization", "senha", "document"])
@pytest.mark.django_db
def test_auditoria_mascara_campos_sensiveis(campo):
    evento = registrar_evento_auditoria(
        acao="teste.sensivel",
        objeto_tipo="teste.Objeto",
        objeto_id="1",
        depois={campo: "valor-secreto"},
        origem="portal",
    )
    assert evento.depois[campo] == REDACTED


@pytest.mark.django_db
def test_auditoria_retira_cnpjcpf_escondido_em_aninhado():
    evento = registrar_evento_auditoria(
        acao="teste.identificador",
        objeto_tipo="teste.Objeto",
        objeto_id="1",
        depois={"cnpjcpf": "12345678000195"},
        origem="portal",
    )
    assert evento.depois["cnpjcpf"] == REDACTED


@pytest.mark.django_db
def test_auditoria_nao_pode_ser_editada_nem_excluida():
    evento = registrar_evento_auditoria(
        acao="teste.imutavel",
        objeto_tipo="teste.Objeto",
        objeto_id="1",
        origem="portal",
    )
    evento.acao = "teste.manipulado"
    with pytest.raises(ValidationError):
        evento.save()

    with pytest.raises(Exception):
        EventoAuditoria.objects.delete()
    with pytest.raises(Exception):
        evento.delete()
