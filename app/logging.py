import logging

REDACTED = "[REDACTED]"

CAMPOS_SENSIVEIS = {"token", "client_secret", "authorization", "senha", "password", "secret", "document", "cpf", "cnpj"}


class RedactingFilter(logging.Filter):
    """Mascara valores em chaves sensíveis do record."""

    def filter(self, record):
        if not hasattr(record, "args") or record.args is None:
            return True
        record.args = tuple(
            REDACTED if any(key in str(arg).lower() for key in CAMPOS_SENSIVEIS) else arg
            for arg in record.args
        )
        return True
