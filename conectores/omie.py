"""
Conector Omie — API REST v1 (app_key + app_secret).

Docs: https://developer.omie.com.br/

Config esperada:
    {"app_key": "...", "app_secret": "..."}
"""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any
from urllib import error, request

import pandas as pd

from .base import ConectorERP

logger = logging.getLogger(__name__)

_BASE_URL = "https://app.omie.com.br/api/v1"


class ConectorOmie(ConectorERP):
    nome = "Omie"

    def _campos_obrigatorios(self) -> list[str]:
        return ["app_key", "app_secret"]

    def buscar_lancamentos(
        self,
        data_inicio: date,
        data_fim: date,
        pagina: int = 1,
        por_pagina: int = 100,
    ) -> pd.DataFrame:
        payload = {
            "call": "ListarContasReceber",
            "app_key": self.config["app_key"],
            "app_secret": self.config["app_secret"],
            "param": [
                {
                    "pagina": pagina,
                    "registros_por_pagina": por_pagina,
                    "filtrar_por_data_de": data_inicio.strftime("%d/%m/%Y"),
                    "filtrar_por_data_ate": data_fim.strftime("%d/%m/%Y"),
                }
            ],
        }
        dados = self._post(f"{_BASE_URL}/financas/contareceber/", payload)
        if not dados or "conta_receber_cadastro" not in dados:
            return pd.DataFrame()

        registros = []
        for item in dados["conta_receber_cadastro"]:
            registros.append(
                {
                    "NF": str(item.get("numero_documento", "")),
                    "Data": item.get("data_emissao", ""),
                    "Vencimento": item.get("data_vencimento", ""),
                    "Valor": float(item.get("valor_documento", 0)),
                    "Categoria": item.get("codigo_categoria_cr", "RECEITA"),
                    "Cliente": item.get("nome_cliente", ""),
                    "Tipo": "RECEITA",
                }
            )
        return self._schema_padrao(registros)

    def _post(self, url: str, payload: dict) -> dict[str, Any]:
        body = json.dumps(payload).encode()
        req = request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json"})
        try:
            with request.urlopen(req, timeout=30) as resp:  # nosec B310
                return json.loads(resp.read())
        except error.URLError as exc:
            logger.error("[Omie] Erro de rede: %s", exc)
            return {}
        except json.JSONDecodeError as exc:
            logger.error("[Omie] Resposta inválida: %s", exc)
            return {}
