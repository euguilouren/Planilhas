"""
Classe abstrata para conectores ERP.
Cada conector implementa buscar_lancamentos() e retorna DataFrame no schema padrão.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import date

import pandas as pd

logger = logging.getLogger(__name__)


class ConectorERP(ABC):
    """Interface comum para todos os conectores ERP."""

    nome: str = "ERP Genérico"

    def __init__(self, config: dict):
        self.config = config
        self._validar_config(config)

    def _validar_config(self, config: dict) -> None:
        """Valida que as credenciais obrigatórias estão presentes."""
        for campo in self._campos_obrigatorios():
            if not config.get(campo):
                raise ValueError(f"[{self.nome}] Campo obrigatório ausente: '{campo}'")

    def _campos_obrigatorios(self) -> list[str]:
        return []

    @abstractmethod
    def buscar_lancamentos(
        self,
        data_inicio: date,
        data_fim: date,
        pagina: int = 1,
        por_pagina: int = 100,
    ) -> pd.DataFrame:
        """
        Retorna DataFrame com lançamentos financeiros no schema padrão:
          NF | Data | Vencimento | Valor | Categoria | Cliente | Tipo
        """

    def sincronizar(
        self,
        data_inicio: date,
        data_fim: date,
        max_paginas: int = 50,
    ) -> pd.DataFrame:
        """Busca todas as páginas e consolida em um único DataFrame."""
        todos: list[pd.DataFrame] = []
        for pagina in range(1, max_paginas + 1):
            df = self.buscar_lancamentos(data_inicio, data_fim, pagina=pagina)
            if df.empty:
                break
            todos.append(df)
            logger.info("[%s] Página %d: %d registros", self.nome, pagina, len(df))
            if len(df) < 100:
                break
        if not todos:
            return pd.DataFrame()
        return pd.concat(todos, ignore_index=True)

    @staticmethod
    def _schema_padrao(registros: list[dict]) -> pd.DataFrame:
        """Garante que o DataFrame de saída tem o schema correto."""
        df = pd.DataFrame(registros)
        colunas = ["NF", "Data", "Vencimento", "Valor", "Categoria", "Cliente", "Tipo"]
        for col in colunas:
            if col not in df.columns:
                df[col] = None
        return df[colunas]
