"""Adaptador Efí (Gerencianet) — GatewayAdapter Protocol.

Credenciais em `ContaGateway.configuracao_criptografada`:
- client_id, client_secret
- certificate_path / certificate_password (mTLS)
- pix_key (para PIX)
- ambiente ("sandbox" | "producao")

Roteamento de webhooks e URLs de produção sofisticados devem ser
concordados com a documentação de homologação. Não chama o provedor real
até o operador providenciar credenciais oficiais.

Specs em `_reversa_sdd/specs/gateways/efi.md`.
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


PIX_BASE_SANDBOX = "https://sandbox.gerencianet.com.br/v2"
PIX_BASE_PROD = "https://api-pix.gerencianet.com.br/v2"


class EfiAdapter:
    """Adaptador Efí — OAuth2 com mTLS (cert + password opcional)."""

    def __init__(self, *, config: dict, ambiente: str = "sandbox",
                 habilita_boleto: bool = True, habilita_pix: bool = True):
        self._config = dict(config or {})
        self._ambiente = (ambiente or "sandbox").lower()
        self._habilita_boleto = bool(habilita_boleto)
        self._habilita_pix = bool(habilita_pix)

    @property
    def _base(self) -> str:
        return PIX_BASE_SANDBOX if self._ambiente == "sandbox" else PIX_BASE_PROD

    def validate_config(self) -> None:
        faltantes = {"client_id", "client_secret"} - set(self._config.keys())
        if faltantes:
            raise GatewayValidationError(
                f"Credenciais Efín ausentes: {sorted(faltantes)}"
            )
        if not self._habilita_boleto and not self._habilita_pix:
            raise GatewayValidationError("Nenhuma forma habilitada nesta conta Efí.")

    def test_connection(self) -> None:
        self._obter_token()

    def is_presentation_url_allowed(self, url: str) -> bool:
        return bool(url) and url.startswith("https://")

    def _obter_token(self) -> str:
        client_id = self._config.get("client_id", "")
        client_secret = self._config.get("client_secret", "")
        if not client_id or not client_secret:
            raise GatewayAuthenticationError(
                "Efí: client_id/client_secret ausentes."
            )
        try:
            import httpx

            basic = f"{client_id}:{client_secret}".encode("utf-8").hex()
            # Real OAuth:
            response = httpx.post(
                f"{self._base}/oauth/token",
                json={"grant_type": "client_credentials"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={"grant_type": "client_credentials"},
                auth=(client_id, client_secret),
                timeout=15.0,
            )
            if response.status_code in (401, 403):
                raise GatewayAuthenticationError(
                    "Efí: credencial expirada/invalida. Revise o client_id/client_secret."
                )
            if response.status_code >= 500:
                raise GatewayTemporaryError(
                    f"Efí: serviço indeterminado (HTTP {response.status_code})"
                )
            if response.status_code < 200 or response.status_code > 299:
                raise GatewayTemporaryError(
                    f"Efí: falha na autenticação (HTTP {response.status_code})"
                )
            return (response.json() or {}).get("access_token", "")
        except GatewayTemporaryError:
            raise
        except GatewayAuthenticationError:
            raise
        except Exception as erro:
            raise GatewayTemporaryError(
                f"Efí: falha de rede/auth {erro}"
            ) from erro

    # ---- impressions
    def issue(self, command: Mapping) -> IssueResult:
        token = self._obter_token()
        meio = command.get("meio", "pix")

        valor_original = str(command.get("valor_original") or "0")

        payload = {
            "calendario": {"expiracao": 3600 if meio == "pix" else 259200},
            "valor": {"original": f"{float(valor_original or '0'):.2f}"},
            "chave": self._config.get("pix_key"),
            "solicitacaoPagador": "Pagamento conforme solicitado",
        }
        path_extra = "v" if meio == "boleto" else ""
        response = _post_json(
            f"{self._base}/cob{path_extra}",
            token,
            payload,
        )
        if response.status_code >= 500:
            raise GatewayTemporaryError("Efí: servidor temporário")
        if response.status_code in (400, 404, 422):
            raise GatewayValidationError(
                f"Efí: problema com dados da cobrança (HTTP {response.status_code})"
            )
        if response.status_code in (401, 403):
            raise GatewayAuthenticationError(
                f"Efí: falha de credencial de gateway ({response.status_code})"
            )
        if response.status_code < 200 or response.status_code > 299:
            raise GatewayTemporaryError(
                f"Efí: resposta estranha HTTP {response.status_code}"
            )

        body = response.json() or {}
        external_id = str(body.get("txid") or "").strip()
        if not external_id:
            return IssueResult(
                external_id="",
                status="failed",
                method=meio,
            )

        endereco = body.get("baseUrl") if body.get("loc", {}).get("url") else None
        return IssueResult(
            external_id=external_id,
            status="issued",
            method=meio,
            digitable_line=(body.get("linha_digitavel") or body.get("boleto", {}).get("linha") or None),
            pix_copy_paste=body.get("pixCopiaECola") or None,
            pix_qr_text=None,
            presentation_url=url_externa(body),
            hybrid=None,
        )

    def query(self, external_id: str) -> QueryResult:
        token = self._obter_token()
        response = _get_json(f"{self._base}/cob/" + str(external_id), token)
        if response.status_code >= 500:
            raise GatewayTemporaryError("Efí: servidor temporário")
        body = response.json() or {}
        status = (body.get("status") or "").upper()
        mapping = {
            "ATIVA": "issued",
            "CONCLUIDA": "paid",
            "REMOVIDA_PELO_USUARIO_RECEBEDOR": "cancelled",
            "REMOVIDA": "cancelled",
        }
        return QueryResult(
            external_id=str(external_id),
            status=mapping.get(status, "unknown"),
            paid_at=None,
            cancelled_at=None,
            valor=Decimal(str(body.get("valor") or "0")),
        )

    def cancel(self, external_id: str, *, idempotencia: str) -> CancelResult:
        from financeiro.gateways.base import CancelResult

        token = self._obter_token()
        response = _post_json(
            f"{self._base}/cob/" + str(external_id) + "/revisao",
            token,
            {"revisao": 0},
        )
        status = (response.json() or {}).get("status", "").upper()
        if status == "REMOVIDA_PELO_USUARIO_RECEBEDOR" or status == "REMOVIDA":
            return CancelResult(str(external_id), "cancelled")
        if status in ("ATIVA", "CONCLUIDA"):
            return CancelResult(str(external_id), "unknown")
        return CancelResult(str(external_id), "unknown")

    def parse_webhook(self, *, headers, body: bytes) -> WebhookEvent:
        payload = json.loads(body.decode() or "{}")
        return WebhookEvent(
            provedor="efi",
            id_evento_externo=str(payload.get("txid") or ""),
            id_referencia_externa=str(payload.get("txid") or ""),
            tipo="paid" if (payload.get("status") or "").upper() == "CONCLUIDA" else "cancelled",
            valor=Decimal(str(payload.get("valor") or "0")),
            ocorreu_em=None if not payload.get("data") else datetime.datetime.fromisoformat(payload["data"]),
        )


def url_externa(body):
    loc = body.get("loc") if isinstance(body.get("loc"), dict) else {}
    return loc.get("url") or body.get("link") or None


def _post_json(url, token, payload):
    import httpx

    response = httpx.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=20.0,
    )
    return response


def _get_json(url, token):
    import httpx

    return httpx.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=20.0,
    )
