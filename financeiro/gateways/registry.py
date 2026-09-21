FACTORIES = {}


PROVEEDORES_PERMITIDOS = {"efi", "sicredi", "sicoob", "fake"}


def register_adapter(provedor, factory):
    provedores_permitidos = PROVEEDORES_PERMITIDOS
    if provedor not in provedores_permitidos:
        raise ValueError(f"Provedor não suportado: {provedor}")
    if provedor in FACTORIES:
        raise ValueError(f"Provedor já registrado: {provedor}")

    FACTORIES[provedor] = factory


def get_adapter(conta):
    from financeiro.crypto import decrypt_config

    factory = FACTORIES.get(conta.provedor)
    if factory is None:
        raise ValueError(f"Provedor não registrado: {conta.provedor}")
    kwargs = {}
    if conta.provedor == "fake":
        kwargs = {
            "allowed_hosts": ["https://fakes.example.com"],
            "hybrid": False,
        }
    adapter = factory(**kwargs)
    return adapter


def _clear():
    FACTORIES.clear()
