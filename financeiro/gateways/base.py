from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Protocol, Mapping


class GatewayTemporaryError(Exception):
    """Indica resultado indefinido; exige reconciliação antes de reemissão."""


class GatewayAuthenticationError(Exception):
    """Credenciais inválidas ou conta inativa no provedor."""


class GatewayValidationError(Exception):
    """Dados exigidos pelo provedor inválidos/ausentes."""


@dataclass(frozen=True)
class GatewayAccountConfig:
    public_id: str
    provedor: str
    ambiente: str
    habilita_boleto: bool
    habilita_pix: bool
    configuracao_publica: dict
    configuracao_criptografada: str


@dataclass(frozen=True)
class IssueCommand:
    cobranca_id: int
    valor: Decimal
    vencimento: str
    documento_pagador: str
    nome_pagador: str
    end_pagador: str
    meio: str
    idempotencia: str


@dataclass(frozen=True)
class IssueResult:
    external_id: str
    status: str          # issued | failed | pending_unknown
    method: str
    digitable_line: str | None = None
    pix_copy_paste: str | None = None
    pix_qr_text: str | None = None
    presentation_url: str | None = None
    hybrid: bool = False


@dataclass(frozen=True)
class QueryResult:
    external_id: str
    status: str          # issued | paid | cancelled | unknown
    paid_at: datetime | None = None
    cancelled_at: datetime | None = None
    valor: Decimal | None = None


@dataclass(frozen=True)
class CancelResult:
    external_id: str
    status: str          # cancelled | unknown


@dataclass(frozen=True)
class WebhookEvent:
    provedor: str
    id_evento_externo: str
    id_referencia_externa: str
    tipo: str            # paid | cancelled | issued
    valor: Decimal | None = None
    ocorreu_em: datetime | None = None


class GatewayAdapter(Protocol):
    def validate_config(self) -> None: ...
    def test_connection(self) -> None: ...
    def is_presentation_url_allowed(self, url: str) -> bool: ...
    def issue(self, command: dict) -> IssueResult: ...
    def query(self, external_id: str) -> QueryResult: ...
    def cancel(self, external_id: str, *, idempotencia: str) -> CancelResult: ...
    def parse_webhook(self, *, headers: Mapping[str, str], body: bytes) -> WebhookEvent: ...
