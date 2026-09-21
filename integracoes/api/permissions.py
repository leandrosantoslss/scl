from integracoes.api.exceptions import EnvelopeError


def exigir_escopo(token, escopo):
    if not token or not token.allow_scopes([escopo]):
        raise EnvelopeError(
            403,
            "scope_not_authorized",
            f"Escopo exigido não autorizado: {escopo}",
        )
    return escopo
