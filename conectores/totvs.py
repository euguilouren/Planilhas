"""
Conector TOTVS Protheus — REST API (auth básica).

Requer módulo FINA020 (Contas a Receber) exposto via REST.

Config esperada:
    {"base_url": "http://totvs-server:8080", "usuario": "...", "senha": "..."}
"""
from __future__ import annotations

import base64
import logging
from datetime import date
from urllib import request, error
import json

import pandas as pd

from .base import ConectorERP

logger = logging.getLogger(__name__)


class ConectorTOTVS(ConectorERP):
    nome = "TOTVS Protheus"

    def _campos_obrigatorios(self) -> list[str]:
        return ["base_url", "usuario", "senha"]

    def _auth_header(self) -> str:
        credencial = f"{self.config['usuario']}:{self.config['senha']}"
        return "Basic " + base64.b64encode(credencial.encode()).decode()

    def buscar_lancamentos(
        self,
        data_inicio: date,
        data_fim: date,
        pagina: int = 1,
        por_pagina: int = 100,
    ) -> pd.DataFrame:
        base_url = self.config["base_url"].rstrip("/")
        url = (
            f"{base_url}/rest/FINA020/receberTitulos"
            f"?dtInicial={data_inicio.strftime('%d/%m/%Y')}"
            f"&dtFinal={data_fim.strftime('%d/%m/%Y')}"
            f"&page={pagina}&pageSize={por_pagina}"
        )
        req = request.Request(url, headers={
            "Authorization": self._auth_header(),
            "Content-Type": "application/json",
        })
        try:
            with request.urlopen(req, timeout=30) as resp:
                dados = json.loads(resp.read())
        except (error.URLError, json.JSONDecodeError) as exc:
            logger.error("[TOTVS] Erro ao buscar lançamentos: %s", exc)
            return pd.DataFrame()

        itens = dados.get("items", dados) if isinstance(dados, dict) else dados
        registros = []
        for item in itens if isinstance(itens, list) else []:
            registros.append({
                "NF":         str(item.get("E1_NUM", item.get("numero", ""))),
                "Data":       item.get("E1_EMISSAO", item.get("dataEmissao", "")),
                "Vencimento": item.get("E1_VENCTO", item.get("dataVencimento", "")),
                "Valor":      float(item.get("E1_VALOR", item.get("valor", 0)) or 0),
                "Categoria":  item.get("E1_NATUREZ", "RECEITA"),
                "Cliente":    item.get("E1_NOMCLI", item.get("nomeCliente", "")),
                "Tipo":       "RECEITA",
            })
        return self._schema_padrao(registros)
