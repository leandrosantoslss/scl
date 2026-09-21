ADMINISTRADOR = "Administrador"
CADASTRO = "Cadastro"
FINANCEIRO = "Financeiro"
CONSULTA = "Consulta"

ROLE_PERMISSION_PREFIXES = {
    ADMINISTRADOR: ("add_", "change_", "delete_", "view_"),
    CADASTRO: ("add_", "change_", "view_"),
    FINANCEIRO: ("view_",),
    CONSULTA: ("view_",),
}
