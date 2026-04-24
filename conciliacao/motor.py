"""
Conciliação bancária — NFs vs extrato OFX/QFX.

Uso:
    df_resultado = conciliar(df_nfs, df_extrato)
    # Status por linha: CONCILIADO | PENDENTE | DIVERGENTE

    df_extrato = LeitorOFX.ler("extrato.ofx")
"""
from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path
from typing import Union

import pandas as pd

logger = logging.getLogger(__name__)

_STATUS_CONCILIADO = "CONCILIADO"
_STATUS_PENDENTE = "PENDENTE"
_STATUS_DIVERGENTE = "DIVERGENTE"

# Tolerâncias de matching
_TOLERANCIA_VALOR = 0.01   # diferença máxima em R$
_TOLERANCIA_DIAS = 3       # janela de ±3 dias úteis


def conciliar(
    df_nfs: pd.DataFrame,
    df_extrato: pd.DataFrame,
    col_data_nf: str = "Data",
    col_valor_nf: str = "Valor",
    col_data_ext: str = "Data",
    col_valor_ext: str = "Valor",
) -> pd.DataFrame:
    """
    Casa NFs com lançamentos do extrato bancário.

    Retorna DataFrame unindo as duas fontes com coluna `Status_Conciliacao`:
      CONCILIADO  — NF casada com lançamento bancário
      PENDENTE    — NF sem lançamento correspondente
      DIVERGENTE  — NF com lançamento em data/valor próximo mas com diferença
    """
    if df_nfs.empty or df_extrato.empty:
        df_nfs = df_nfs.copy()
        df_nfs["Status_Conciliacao"] = _STATUS_PENDENTE
        df_nfs["Lançamento_Banco"] = None
        df_nfs["Diferença_RS"] = None
        return df_nfs

    nfs = df_nfs.copy()
    ext = df_extrato.copy()

    nfs["_data_dt"] = pd.to_datetime(nfs[col_data_nf], dayfirst=True, errors="coerce")
    ext["_data_dt"] = pd.to_datetime(ext[col_data_ext], dayfirst=True, errors="coerce")
    nfs["_valor_f"] = pd.to_numeric(nfs[col_valor_nf], errors="coerce").fillna(0).abs()
    ext["_valor_f"] = pd.to_numeric(ext[col_valor_ext], errors="coerce").fillna(0).abs()

    usados = set()
    resultados = []

    for idx_nf, nf in nfs.iterrows():
        data_nf = nf["_data_dt"]
        valor_nf = nf["_valor_f"]
        if pd.isna(data_nf):
            resultados.append((idx_nf, _STATUS_PENDENTE, None, None))
            continue

        janela_inf = data_nf - timedelta(days=_TOLERANCIA_DIAS)
        janela_sup = data_nf + timedelta(days=_TOLERANCIA_DIAS)
        candidatos = ext[
            (ext["_data_dt"] >= janela_inf)
            & (ext["_data_dt"] <= janela_sup)
            & (~ext.index.isin(usados))
        ]

        # Match exato de valor
        match_exato = candidatos[
            (candidatos["_valor_f"] - valor_nf).abs() <= _TOLERANCIA_VALOR
        ]
        if not match_exato.empty:
            idx_ext = match_exato.index[0]
            usados.add(idx_ext)
            resultados.append((idx_nf, _STATUS_CONCILIADO, idx_ext, 0.0))
            continue

        # Match próximo (valor divergente mas data na janela)
        if not candidatos.empty:
            diff_series = (candidatos["_valor_f"] - valor_nf).abs()
            idx_closest = diff_series.sort_values().index[0]
            closest = candidatos.loc[idx_closest]
            diff = round(float(closest["_valor_f"]) - float(valor_nf), 2)
            usados.add(idx_closest)
            resultados.append((idx_nf, _STATUS_DIVERGENTE, None, diff))
            continue

        resultados.append((idx_nf, _STATUS_PENDENTE, None, None))

    status_map = {r[0]: r[1] for r in resultados}
    ext_map = {r[0]: r[2] for r in resultados}
    diff_map = {r[0]: r[3] for r in resultados}

    nfs["Status_Conciliacao"] = nfs.index.map(status_map)
    nfs["Idx_Lançamento"] = nfs.index.map(ext_map)
    nfs["Diferença_RS"] = nfs.index.map(diff_map)
    nfs = nfs.drop(columns=["_data_dt", "_valor_f"])
    return nfs


class LeitorOFX:
    """Lê arquivos OFX/QFX e retorna DataFrame com colunas Data e Valor."""

    @staticmethod
    def ler(caminho: Union[str, Path]) -> pd.DataFrame:
        """
        Lê um arquivo OFX e retorna DataFrame com colunas:
          Data | Valor | Descricao | ID_Transacao
        """
        caminho = Path(caminho)
        if not caminho.exists():
            raise FileNotFoundError(f"Arquivo OFX não encontrado: {caminho}")

        try:
            return LeitorOFX._ler_com_ofxparse(caminho)
        except ImportError:
            return LeitorOFX._ler_manual(caminho)

    @staticmethod
    def _ler_com_ofxparse(caminho: Path) -> pd.DataFrame:
        import ofxparse  # noqa: PLC0415

        with open(caminho, "rb") as f:
            ofx = ofxparse.OfxParser.parse(f)

        registros = []
        for conta in ofx.account if hasattr(ofx, "account") else [ofx.account]:
            for transacao in conta.statement.transactions:
                registros.append({
                    "Data": transacao.date.strftime("%d/%m/%Y") if transacao.date else None,
                    "Valor": float(transacao.amount),
                    "Descricao": str(transacao.memo or transacao.payee or ""),
                    "ID_Transacao": str(transacao.id or ""),
                })

        if not registros:
            return pd.DataFrame(columns=["Data", "Valor", "Descricao", "ID_Transacao"])
        return pd.DataFrame(registros)

    @staticmethod
    def _ler_manual(caminho: Path) -> pd.DataFrame:
        """Parser OFX mínimo sem dependências externas."""
        import re

        content = caminho.read_text(encoding="utf-8", errors="replace")
        registros = []
        for bloco in re.findall(r"<STMTTRN>(.*?)</STMTTRN>", content, re.DOTALL):
            def _tag(tag_name: str) -> str:
                m = re.search(rf"<{tag_name}>(.*?)(?:<|\n)", bloco, re.DOTALL)
                return m.group(1).strip() if m else ""

            data_raw = _tag("DTPOSTED")
            if len(data_raw) >= 8:
                data_fmt = f"{data_raw[6:8]}/{data_raw[4:6]}/{data_raw[0:4]}"
            else:
                data_fmt = None

            try:
                valor = float(_tag("TRNAMT").replace(",", "."))
            except (ValueError, TypeError):
                valor = 0.0

            registros.append({
                "Data": data_fmt,
                "Valor": valor,
                "Descricao": _tag("MEMO") or _tag("NAME"),
                "ID_Transacao": _tag("FITID"),
            })

        if not registros:
            return pd.DataFrame(columns=["Data", "Valor", "Descricao", "ID_Transacao"])
        return pd.DataFrame(registros)
