FACTORIES = {}


def _factories_iniciais():
    """Registra adaptadores oficiais padrão. Cada factory recebe a config
    de conta (dict) já descriptografada + ambiente/habilita_* via kwargs."""
    from financeiro.gateways.efi import EfiAdapter
    from financeiro.gateways.sicredi import SicrediAdapter
    from financeiro.gateways.sicoob import SicoobAdapter

    FACTORIES.setdefault("efi", EfiAdapter)
    FACTORIES.setdefault("sicredi", SicrediAdapter)
    FACTORIES.setdefault("sicoob", SicoobAdapter)


_factories_iniciais()


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
    else:
        config = decrypt_config(conta.configuracao_criptografada) if conta.configuracao_criptografada else {}
        kwargs = {
            "config": config,
            "ambiente": getattr(conta, "ambiente", "sandbox"),
            "habilita_boleto": getattr(conta, "habilita_boleto", False),
            "habilita_pix": getattr(conta, "habilita_pix", False),
        }
    adapter = factory(**kwargs)
    return adapter


def _clear():
    FACTORIES.clear()
