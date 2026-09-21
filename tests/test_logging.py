from io import StringIO
import logging

import pytest

from app.logging import RedactingFilter, REDACTED


def _construir_sink():
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(RedactingFilter())
    return stream, handler


@pytest.mark.parametrize(
    "palavra", ["authorization", "token", "client_secret", "senha", "password", "secret", "document"]
)
def test_redaction_mascara_valores_sensiveis(palavra):
    stream, handler = _construir_sink()
    logger = logging.getLogger("app.redacting-test")
    logger.addHandler(handler)
    logger.propagate = False
    logger.error("falha autêntica %s", f"{palavra}=VALOR_SECRETO")
    logger.removeHandler(handler)
    conteudo = stream.getvalue()
    assert REDACTED in conteudo
    assert "VALOR_SECRETO" not in conteudo
