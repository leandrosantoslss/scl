from django.core.exceptions import ValidationError

from integracoes.models import AuthorityMode
from integracoes.services.policies import RECURSO_POR_MODELO, _politica
from integracoes.models import PoliticaIntegracao, Recurso


def rejeitar_campos_protegidos(modelo_cls, dados_limpos):
    """Servidor é a única autoridade: campos sob LEGACY_MASTER não podem
    ser alterados por POST forjado no portal nem pela API.

    Modelos sem recurso mapeado (ex.: `Sistema`) passam sem restrição
    porque o contrato da API administrativa define autoridade apenas
    para cliente, assinatura, cobrança e pagamento.
    """
    chave = f"{modelo_cls._meta.app_label}.{modelo_cls.__name__}"
    recurso = RECURSO_POR_MODELO.get(chave)
    if recurso is None:
        return
    politicas = PoliticaIntegracao.objects.filter(
        recurso=recurso, modo=AuthorityMode.LEGACY_MASTER
    )
    for politica in politicas.iterator():
        protegidos = set(politica.writable_fields or [])
        intersecao = protegidos.intersection(dados_limpos)
        if intersecao:
            raise ValidationError(
                {
                    campo: f"Campo sob autoridade do legado ({politica.integration.nome}); alteração recusada."
                    for campo in intersecao
                }
            )
