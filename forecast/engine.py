"""
Forecast de fluxo de caixa — projeção 30/60/90 dias.

Algoritmo: média móvel dos últimos 3 meses por categoria de receita/despesa.
Gera alertas automáticos de saldo negativo projetado.

Uso:
    df_proj = ForecastEngine.projetar(df_processado, dias=[30, 60, 90])
    alertas = ForecastEngine.alertas(df_proj)
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import List

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class ForecastEngine:
    """Projeta receitas e despesas futuras com base em histórico recente."""

    @staticmethod
    def projetar(
        df: pd.DataFrame,
        col_data: str = "Data",
        col_valor: str = "Valor",
        col_tipo: str = "Tipo",
        dias: List[int] = None,
        meses_historico: int = 3,
    ) -> pd.DataFrame:
        """
        Projeta fluxo de caixa para os horizontes especificados em *dias*.

        Retorna DataFrame com colunas:
          Data_Proj | Receita_Proj | Despesa_Proj | Saldo_Proj | Alerta
        """
        if dias is None:
            dias = [30, 60, 90]

        df = df.copy()
        df["_data"] = pd.to_datetime(df[col_data], dayfirst=True, errors="coerce")
        df["_valor"] = pd.to_numeric(df[col_valor], errors="coerce").fillna(0)

        df_valido = df.dropna(subset=["_data"])
        if df_valido.empty:
            return _df_vazio()

        data_max = df_valido["_data"].max()
        data_corte = data_max - pd.DateOffset(months=meses_historico)
        df_hist = df_valido[df_valido["_data"] >= data_corte]

        # Médias mensais por tipo
        rec_mensal = _media_mensal(df_hist, col_tipo, "RECEITA", "_valor")
        desp_mensal = _media_mensal(df_hist, col_tipo, "DESPESA", "_valor")

        # Projeção diária (média mensal / 30)
        rec_dia = rec_mensal / 30
        desp_dia = desp_mensal / 30

        hoje = date.today()
        linhas = []
        saldo_acumulado = 0.0
        for d in range(1, max(dias) + 1):
            data_proj = hoje + timedelta(days=d)
            rec = round(rec_dia * d, 2) if d <= max(dias) else 0.0
            desp = round(desp_dia * d, 2)
            saldo = round(rec - desp, 2)
            saldo_acumulado += (rec_dia - desp_dia)
            if d in dias:
                linhas.append({
                    "Horizonte_Dias": d,
                    "Data_Proj": data_proj.strftime("%d/%m/%Y"),
                    "Receita_Proj": round(rec_dia * d, 2),
                    "Despesa_Proj": round(desp_dia * d, 2),
                    "Saldo_Proj": round(saldo_acumulado, 2),
                    "Alerta": "⚠️ SALDO NEGATIVO" if saldo_acumulado < 0 else "✅ OK",
                })

        return pd.DataFrame(linhas)

    @staticmethod
    def projetar_diario(
        df: pd.DataFrame,
        col_data: str = "Data",
        col_valor: str = "Valor",
        col_tipo: str = "Tipo",
        dias: int = 30,
        meses_historico: int = 3,
    ) -> pd.DataFrame:
        """
        Projeção dia a dia para os próximos *dias* dias.
        Útil para o gráfico de linha pontilhada no dashboard.

        Retorna DataFrame com colunas:
          Data_Proj | Receita_Proj | Despesa_Proj | Saldo_Proj
        """
        df = df.copy()
        df["_data"] = pd.to_datetime(df[col_data], dayfirst=True, errors="coerce")
        df["_valor"] = pd.to_numeric(df[col_valor], errors="coerce").fillna(0)

        df_valido = df.dropna(subset=["_data"])
        if df_valido.empty:
            return _df_vazio_diario()

        data_corte = df_valido["_data"].max() - pd.DateOffset(months=meses_historico)
        df_hist = df_valido[df_valido["_data"] >= data_corte]

        rec_mensal = _media_mensal(df_hist, col_tipo, "RECEITA", "_valor")
        desp_mensal = _media_mensal(df_hist, col_tipo, "DESPESA", "_valor")
        rec_dia = rec_mensal / 30
        desp_dia = desp_mensal / 30

        hoje = date.today()
        saldo = 0.0
        linhas = []
        for d in range(1, dias + 1):
            saldo += rec_dia - desp_dia
            linhas.append({
                "Data_Proj": (hoje + timedelta(days=d)).strftime("%d/%m/%Y"),
                "Receita_Proj": round(rec_dia, 2),
                "Despesa_Proj": round(desp_dia, 2),
                "Saldo_Proj": round(saldo, 2),
            })
        return pd.DataFrame(linhas)

    @staticmethod
    def alertas(df_proj: pd.DataFrame) -> List[str]:
        """Retorna lista de textos de alerta com base na projeção."""
        alertas = []
        negativos = df_proj[df_proj.get("Saldo_Proj", pd.Series(dtype=float)) < 0]
        if not negativos.empty:
            primeiro = negativos.iloc[0]
            alertas.append(
                f"Saldo projetado negativo em {primeiro.get('Horizonte_Dias', '?')} dias "
                f"(R$ {primeiro.get('Saldo_Proj', 0):,.2f})"
            )
        return alertas


def _media_mensal(df: pd.DataFrame, col_tipo: str, tipo: str, col_valor: str) -> float:
    """Média mensal absoluta dos valores de um determinado tipo."""
    if col_tipo not in df.columns:
        # Fallback por sinal do valor
        mask = df[col_valor] >= 0 if tipo == "RECEITA" else df[col_valor] < 0
    else:
        mask = df[col_tipo].str.upper() == tipo.upper()

    sub = df[mask][col_valor].abs()
    if sub.empty:
        return 0.0

    # Agrupa por mês e calcula média
    datas = df[mask]["_data"].dropna()
    if datas.empty:
        return float(sub.sum())

    n_meses = max(1, (datas.max() - datas.min()).days / 30)
    return float(sub.sum() / n_meses)


def _df_vazio() -> pd.DataFrame:
    return pd.DataFrame(columns=["Horizonte_Dias", "Data_Proj", "Receita_Proj", "Despesa_Proj", "Saldo_Proj", "Alerta"])


def _df_vazio_diario() -> pd.DataFrame:
    return pd.DataFrame(columns=["Data_Proj", "Receita_Proj", "Despesa_Proj", "Saldo_Proj"])
