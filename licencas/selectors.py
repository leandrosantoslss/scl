from django.db.models import Q

from licencas.models import Cliente, Sistema
from licencas.validators import normalize_document


def listar_clientes(*, q="", status=""):
    queryset = Cliente.objects.all().order_by("nome", "pk")
    if q:
        document = normalize_document(q)
        if document:
            queryset = queryset.filter(
                Q(nome__icontains=q) | Q(cnpjcpf__icontains=document)
            )
        else:
            queryset = queryset.filter(Q(nome__icontains=q))
    if status == "active":
        queryset = queryset.filter(ativo=True, bloqueado=False)
    elif status == "blocked":
        queryset = queryset.filter(bloqueado=True)
    elif status == "inactive":
        queryset = queryset.filter(ativo=False)
    return queryset


def listar_assinaturas(*, cliente="", sistema="", periodicidade="", status=""):
    from licencas.models import ClienteSistema

    queryset = ClienteSistema.objects.select_related("cliente", "sistema").order_by("pk")
    if cliente:
        queryset = queryset.filter(cliente_id=cliente)
    if sistema:
        queryset = queryset.filter(sistema_id=sistema)
    if periodicidade:
        queryset = queryset.filter(periodicidade=periodicidade)
    if status == "active":
        queryset = queryset.filter(ativo=True, bloqueado=False)
    elif status == "blocked":
        queryset = queryset.filter(bloqueado=True)
    elif status == "inactive":
        queryset = queryset.filter(ativo=False)
    return queryset


def listar_sistemas(*, q="", status=""):
    queryset = Sistema.objects.all().order_by("nome", "pk")
    if q:
        queryset = queryset.filter(Q(nome__icontains=q) | Q(codigo__icontains=q))
    if status == "active":
        queryset = queryset.filter(ativo=True)
    elif status == "inactive":
        queryset = queryset.filter(ativo=False)
    return queryset
