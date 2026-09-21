class IntegrationPermissionDenied(Exception):
    """Política/escopo/campo não autorizado para a integração."""


class IntegrationConflict(Exception):
    """Conflito de identidade externa, versão ou idempotência."""


class EnvelopeError(Exception):
    """Erro previsto da API com envelope {code, message, details}."""

    def __init__(self, status, code, mensagem, details=None):
        super().__init__(code)
        self.status = status
        self.code = code
        self.mensagem = mensagem
        self.details = details
