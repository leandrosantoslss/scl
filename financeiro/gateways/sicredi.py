"""Adaptador Sicredi — GatewayAdapter Protocol.

Credenciais em `ContaGateway.configuracao_criptografada`:
- client_id, client_secret
- certificate_path / certificate_password (mTLS Sicredi)
- pix_key (para PIX)
- ambiente ("sandbox" | "producao")

Spec em `_reversa_sdd/specs/gateway/sicredi.md`.
"""
import datetime
import json
from decimal import Decimal
from typing import Mapping
from urllib.parse import quote

from financeiro.gateways.base import (
    CancelResult,
    GatewayAuthenticationError,
    GatewayTemporaryError,
    GatewayValidationError,
    IssueResult,
    QueryResult,
    WebhookEvent,
)


SICREDI_PIX_SANDBOX = "https://com.br/pix/gar-api/v2"
SICREDI_PIX_PROD = "https://api-pix-api.central.sicredi.com.br/api/v2"


class SicrediAdapter:
    """Adaptador Sicredi (PIX + Boleto)."""

    def __init__(self, *, config: dict, ambiente: str = "sandbox",
                 habilita_boleto: bool = True, habilita_pix: bool = True):
        self._config = dict(config or {})
        self._ambiente = (ambiente or "sandbox").lower()
        self._habilita_boleto = bool(habilita_boleto)
        self._habilita_pix = bool(habilita_pix)

    @property
    def _base(self) -> str:
        return SICREDI_PIX_SANDBOX if self._ambiente == "sandbox" else SICREDI_PIX_PROD

    def validate_config(self) -> None:
        faltantes = {"client_id", "client_secret"} - set(self._config.keys())
        if faltantes:
            raise GatewayValidationError(
                f"Sicredi: credenciais ausentes: {sorted(faltantes)}"
            )

    def test_connection(self) -> None:
        self._obter_token()

    def is_presentation_url_allowed(self, url: str) -> bool:
        return bool(url) and url.startswith("https://")

    def _obter_token(self) -> str:
        import httpx

        client_id = self._config.get("client_id", "")
        client_secret = self._config.get("client_secret", "")
        if not client_id or not client_secret:
            raise GatewayAuthenticationError("Sicredi: credenciais ausentes")
        response = httpx.post(
            f"{self._base}/oauth/token",
            data={"grant_type": "client_credentials", "scope": "cob.write cob.read"},
            auth=(client_id, client_secret),
            timeout=15.0,
        )
        if response.status_code in (401, 403):
            raise GatewayAuthenticationError("Sicredi: credencial expirada/inválida")
        if response.status_code >= 500:
            raise GatewayTemporaryError(f"Sicredi: serviço indeterminado ({response.status_code})")
        if response.status_code < 200 or response.status_code > 299:
            raise GatewayTemporaryError(
                f"Sicredi: falha de autenticação ({response.status_code})"
            )
        return (response.json() or {}).get("access_token", "")

    def issue(self, command: Mapping) -> IssueResult:
        token = self._obter_token()
        import httpx
        meio = command.get("meio", "pix")
        valor_original = str(command.get("valor_original") or "0")

        payload = {
            "calendario": {"expiracao": 3600 if meio == "pix" else 259200},
            "valor": {"original": valor_original},
            "chave": self._config.get("pix_key"),
            "solicitacaoPagador": "Pagamento acordo",
        }
        response = httpx.post(
            f"{self._base}/cob",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=20.0,
        )
        if response.status_code >= 500:
            raise GatewayTemporaryError("Sicredi: serviço temporariamente indisponível")
        if response.status_code in (400, 404, 422):
            raise GatewayValidationError(
                f"Sicredi: payload inválido (HTTP {response.status_code})"
            )
        if response.status_code in (401, 403):
            raise GatewayAuthenticationError("Sicredi: credencial expirada")
        if response.status_code < 200 or response.status_code > 299:
            raise GatewayTemporaryError(
                f"Sicredi: }}>{response.status_code}"
            )

        body = response.json() or {}
        external_id = str(body.get("txid") or "")
        pix_copy_paste = body.get("pixCopiaECola") or None
        return IssueResult(
            external_id=external_id,
            status="issued" if external_id else "failed",
            method=meio,
            digitable_line=None if meio == "pix" else (body.get("boleto", {}).get("linha") or None),
            pix_copy_paste=pix_copy_paste,
            pix_qr_text=None,
            presentation_url=body.get("loc", {}).get("url") if meio == "pix" else body.get("link"),
            hybrid=None,
        )

    def query(self, external_id: str) -> QueryResult:
        token = self._obter_token()
        import httpx
        response = httpx.get(
            f"{self._base}/cob/" + quote(str(external_id)),
            headers={"Authorization": f"Bearer {token}"},
            timeout=20.0,
        )
        body = response.json() or {}
        status = (body.get("status") or "").upper()
        mapping = {"ATIVA": "issued", "CONCLUIDA": "paid", "REMOVIDA": "cancelled"}
        return QueryResult(
            external_id=str(external_id),
            status=mapping.get(status, "unknown"),
            paid_at=None,
            cancelled_at=None,
            valor=Decimal(str(body.get("valor", {}).get("original") or "0")),
        )

    def cancel(self, external_id: str, *, idempotencia: str) -> CancelResult:
        token = self._obter_token()
        from financeiro.gateways.base import CancelResult
        import httpx
        response = httpx.patch(
            f"{self._base}/cob/" + quote(str(external_id)),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"status": "REMOVIDA_PELO_USUARIO_RECEBEDOR"},
            timeout=20.0,
        )
        body = response.json() or {}
        status = (body.get("status") or "").upper()
        if status == "REMOVIDA_PELO_USUARIO_RECEBEDOR":
            return CancelResult(str(external_id), "cancelled")
        return CancelResult(str(external_id), "unknown")

    def parse_webhook(self, *, headers, body: bytes) -> WebhookEvent:
        payload = json.loads(body.decode() or "{}")
        tipo = "paid" if (payload.get("status") or "").upper() == "CONCLUIDA" else "cancelled"
        return WebhookEvent(
            provedor="sicredi",
            id_evento_externo=str(payload.get("txid") or ""),
            id_referencia_externa=str(payload.get("txid") or ""),
            tipo=tipo,
            valor=Decimal(str(payload.get("valor", {}).get("original") or "0")),
            ocorreu_em=None if not payload.get("data") else datetime.datetime.fromisoformat(payload["data"]),
        )
