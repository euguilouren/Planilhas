"""
Conector Conta Azul — API REST v1 (OAuth2 client_credentials).

Docs: https://developers.contaazul.com/

Config esperada:
    {"client_id": "...", "client_secret": "..."}
"""

from __future__ import annotations

import json
import logging
from datetime import date
from urllib import error, request

import pandas as pd

from .base import ConectorERP

logger = logging.getLogger(__name__)

_TOKEN_URL = "https://api.contaazul.com/auth/token"
_BASE_URL = "https://api.contaazul.com/v1"


class ConectorContaAzul(ConectorERP):
    nome = "Conta Azul"

    def _campos_obrigatorios(self) -> list[str]:
        return ["client_id", "client_secret"]

    def _obter_token(self) -> str:
        payload = json.dumps(
            {
                "grant_type": "client_credentials",
                "client_id": self.config["client_id"],
                "client_secret": self.config["client_secret"],
            }
        ).encode()
        req = request.Request(_TOKEN_URL, data=payload, method="POST", headers={"Content-Type": "application/json"})
        try:
            with request.urlopen(req, timeout=15) as resp:  # nosec B310
                return json.loads(resp.read()).get("access_token", "")
        except (error.URLError, json.JSONDecodeError) as exc:
            logger.error("[ContaAzul] Falha ao obter token: %s", exc)
            return ""

    def buscar_lancamentos(
        self,
        data_inicio: date,
        data_fim: date,
        pagina: int = 1,
        por_pagina: int = 100,
    ) -> pd.DataFrame:
        token = self._obter_token()
        if not token:
            return pd.DataFrame()

        url = (
            f"{_BASE_URL}/receivables"
            f"?emission_start={data_inicio.isoformat()}"
            f"&emission_end={data_fim.isoformat()}"
            f"&page={pagina}&page_size={por_pagina}"
        )
        req = request.Request(url, headers={"Authorization": f"Bearer {token}"})
        try:
            with request.urlopen(req, timeout=30) as resp:  # nosec B310
                items = json.loads(resp.read())
        except (error.URLError, json.JSONDecodeError) as exc:
            logger.error("[ContaAzul] Erro ao buscar lançamentos: %s", exc)
            return pd.DataFrame()

        registros = []
        for item in items if isinstance(items, list) else []:
            registros.append(
                {
                    "NF": str(item.get("number", "")),
                    "Data": item.get("emission_date", "")[:10].replace("-", "/")[::-1].replace("/", "-"),
                    "Vencimento": item.get("due_date", "")[:10],
                    "Valor": float(item.get("value", 0)),
                    "Categoria": item.get("category_name", "RECEITA"),
                    "Cliente": item.get("customer_name", ""),
                    "Tipo": "RECEITA",
                }
            )
        return self._schema_padrao(registros)
