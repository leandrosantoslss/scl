# Matriz de contrato de gateways

Objetivo: mapa explicito entre os metodos `GatewayAdapter`, estados e meios.

- Emitir: emissao externa de boleto ou PIX na conta do provedor.
- Consultar: estado normalizado com paid_at / cancelled_at / valor.
- Cancelar: cancelamento com chave de idempotencia propria.
- ParseWebhook: verificacao de assinatura com bytes brutos.

Cada `GatewayAdapter` e mapeado aos metodos oficiais por provedor ou a uma
capability explicitamente nao-suportada. O primeiro release de producao exige
issue/query/cancel/webhook/payment nos dois meios habilitados para CADA
contrato efetivo (boleto, PIX ou ambos).
