from __future__ import annotations

import secrets
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal
from typing import Mapping

from financeiro.gateways.base import (
    CancelResult,
    GatewayAuthenticationError,
    GatewayValidationError,
    IssueResult,
    QueryResult,
    WebhookEvent,
    GatewayTemporaryError,
)


class FakeAdapter:
    """Adaptador determinístico de teste com estado global por provider."""

    _SHARED_EMITIDOS: dict = {}
    _SHARED_PEDIDOS: list = []

    def __init__(self, *, timeout_behavior=False, invalid_credentials=False,
                 hybrid=False, allowed_hosts=()):
        self._timeout = timeout_behavior
        self._invalid = invalid_credentials
        self._hybrid = hybrid
        self._allowed_hosts = set(allowed_hosts)
        self._emitidos = self._SHARED_EMITIDOS
        self._pedidos = self._SHARED_PEDIDOS

    # ----- config / connection
    def validate_config(self) -> None:
        if self._invalid:
            raise GatewayAuthenticationError("credenciais inválidas (fake)")

    def test_connection(self) -> None:
        if self._invalid:
            raise GatewayAuthenticationError("credenciais inválidas (fake)")

    def is_presentation_url_allowed(self, url: str) -> bool:
        if not self._allowed_hosts:
            return False
        for host in self._allowed_hosts:
            if url.startswith(f"{host}/"):
                return True
        return False

    # ----- issue/query/cancel
    def issue(self, command: dict) -> IssueResult:
        if self._invalid:
            raise GatewayAuthenticationError("credenciais inválidas (fake)")
        if command.get("meio") not in ("pix", "boleto", "ambas"):
            raise GatewayValidationError(f"Meio não suportado: {command.get('meio')}")
        if getattr(self, "_timeout", False):
            raise GatewayTemporaryError("indeterminado (fake timeout)")
        if command["idempotencia"] in (c.get("idempotencia") for c in self._pedidos):
            prev = next(c for c in self._pedidos if c["idempotencia"] == command["idempotencia"])
            result = prev.get("resultado")
            return result

        external_id = f"fake-{secrets.token_urlsafe(8)}"
        pix = command.get("meio") == "pix"
        result = IssueResult(
            external_id=external_id,
            status="issued",
            method=command.get("meio") or "pix",
            digitable_line=None if pix or self._hybrid else "123",
            pix_copy_paste="fake-pix-code" if pix or self._hybrid else None,
            pix_qr_text=None,
            presentation_url=f"https://fakes.example.com/boleto/{external_id}" if not pix else None,
            hybrid=self._hybrid,
        )
        self._pedidos.append({**command})
        self._emitidos[external_id] = {
            "comando": command,
            "status": "issued",
            "paid_at": None,
            "cancelled_at": None,
        }
        return result

    def query(self, external_id: str) -> QueryResult:
        dados = self._emitidos.get(external_id)
        if not dados:
            return QueryResult(external_id, "unknown")
        status = "issued"
        if dados["paid_at"]:
            status = "paid"
        elif dados["cancelled_at"]:
            status = "cancelled"
        return QueryResult(
            external_id=external_id,
            status=status,
            paid_at=dados["paid_at"],
            cancelled_at=dados["cancelled_at"],
            valor=dados["comando"]["valor"],
        )

    def cancel(self, external_id: str, *, idempotencia: str) -> CancelResult:
        dados = self._emitidos.get(external_id)
        if not dados or dados["cancelled_at"] or dados["paid_at"]:
            return CancelResult(external_id, "unknown")
        dados["cancelled_at"] = datetime.now(dt_timezone.utc)
        return CancelResult(external_id, "cancelled")

    def parse_webhook(self, *, headers, body: bytes) -> WebhookEvent:
        import json

        payload = json.loads(body.decode())
        return WebhookEvent(
            provedor="fake",
            id_evento_externo=payload["id_evento"],
            id_referencia_externa=payload["id_referencia"],
            tipo=payload["tipo"],
            valor=payload.get("valor"),
            ocorreu_em=payload.get("ocorreu_em"),
        )

    def simular_pagamento(self, external_id: str):
        self._emitidos[external_id]["paid_at"] = datetime.now(dt_timezone.utc)

    def cancela_internamente(self, external_id: str):
        self._emitidos[external_id]["cancelled_at"] = datetime.now(dt_timezone.utc)
