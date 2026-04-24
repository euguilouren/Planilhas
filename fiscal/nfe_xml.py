"""
Parser de NF-e XML — extrai campos e normaliza para o schema do toolkit.

Suporta NF-e v4.0 (namespace http://www.portalfiscal.inf.br/nfe).

Uso:
    df = ParserNFe.ler_xml("nota.xml")
    df = ParserNFe.ler_pasta("pasta_xmls/")  # processa todos os .xml recursivamente
"""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Union

import pandas as pd

logger = logging.getLogger(__name__)

_NS = "http://www.portalfiscal.inf.br/nfe"
_NS_MAP = {"nfe": _NS}


class ParserNFe:
    """Lê XMLs de NF-e e retorna DataFrame no schema padrão do toolkit."""

    @staticmethod
    def ler_xml(caminho: Union[str, Path]) -> pd.DataFrame:
        """Parseia um único arquivo XML de NF-e."""
        try:
            tree = ET.parse(str(caminho))
            root = tree.getroot()
            registro = _extrair_campos(root, str(caminho))
            if registro:
                return pd.DataFrame([registro])
        except ET.ParseError as exc:
            logger.warning("XML inválido em %s: %s", caminho, exc)
        except Exception as exc:
            logger.warning("Erro ao processar %s: %s", caminho, exc)
        return pd.DataFrame()

    @staticmethod
    def ler_pasta(pasta: Union[str, Path], recursivo: bool = True) -> pd.DataFrame:
        """Processa todos os XMLs de NF-e em uma pasta."""
        pasta = Path(pasta)
        padrao = "**/*.xml" if recursivo else "*.xml"
        xmls = list(pasta.glob(padrao))
        logger.info("Encontrados %d XMLs em %s", len(xmls), pasta)

        registros: List[dict] = []
        for xml_path in xmls:
            df = ParserNFe.ler_xml(xml_path)
            if not df.empty:
                registros.extend(df.to_dict("records"))

        if not registros:
            return pd.DataFrame()
        return pd.DataFrame(registros)

    @staticmethod
    def para_schema_padrao(df: pd.DataFrame) -> pd.DataFrame:
        """Converte colunas do parser NF-e para o schema padrão do toolkit."""
        mapa = {
            "chave_acesso": "NF",
            "data_emissao": "Data",
            "data_vencimento": "Vencimento",
            "valor_total": "Valor",
            "natureza_operacao": "Categoria",
            "nome_destinatario": "Cliente",
            "tipo_nfe": "Tipo",
        }
        df = df.rename(columns={k: v for k, v in mapa.items() if k in df.columns})
        # Garantir schema mínimo
        for col in ["NF", "Data", "Valor", "Categoria", "Cliente"]:
            if col not in df.columns:
                df[col] = None
        return df


def _extrair_campos(root: ET.Element, origem: str) -> dict:
    """Extrai campos principais de um elemento raiz NF-e."""
    infNFe = (
        root.find(f".//{{{_NS}}}infNFe")
        or root.find(".//infNFe")
    )
    if infNFe is None:
        return {}

    def txt(xpath: str, default: str = "") -> str:
        el = infNFe.find(xpath.replace("nfe:", f"{{{_NS}}}"), {})
        if el is None:
            # tenta sem namespace
            el = infNFe.find(xpath.replace("nfe:", ""))
        return el.text.strip() if el is not None and el.text else default

    # Chave de acesso — no atributo Id do infNFe (começa com 'NFe')
    chave = (infNFe.get("Id") or "").replace("NFe", "")

    # Campos de identificação
    ide_ns = f"{{{_NS}}}ide"
    emit_ns = f"{{{_NS}}}emit"
    dest_ns = f"{{{_NS}}}dest"
    total_ns = f"{{{_NS}}}total"
    cobr_ns = f"{{{_NS}}}cobr"

    data_emissao = txt(f"nfe:ide/nfe:dhEmi") or txt("ide/dhEmi")
    data_emissao = _formatar_data(data_emissao)

    tipo_raw = txt("nfe:ide/nfe:tpNF") or txt("ide/tpNF")
    tipo = "RECEITA" if tipo_raw == "1" else "DESPESA"  # 0=entrada(compra), 1=saída(venda)

    natureza = txt("nfe:ide/nfe:natOp") or txt("ide/natOp")

    nome_emit = txt("nfe:emit/nfe:xNome") or txt("emit/xNome")
    nome_dest = txt("nfe:dest/nfe:xNome") or txt("dest/xNome")
    cnpj_dest = txt("nfe:dest/nfe:CNPJ") or txt("dest/CNPJ")

    valor_nf = txt("nfe:total/nfe:ICMSTot/nfe:vNF") or txt("total/ICMSTot/vNF")
    try:
        valor_float = float(valor_nf) if valor_nf else 0.0
        if tipo == "DESPESA":
            valor_float = -valor_float
    except ValueError:
        valor_float = 0.0

    # Vencimento (primeira duplicata, se houver)
    vencimento = txt("nfe:cobr/nfe:dup/nfe:dVenc") or txt("cobr/dup/dVenc")
    vencimento = _formatar_data(vencimento) if vencimento else data_emissao

    return {
        "chave_acesso": chave,
        "data_emissao": data_emissao,
        "data_vencimento": vencimento,
        "valor_total": valor_float,
        "natureza_operacao": natureza,
        "nome_emitente": nome_emit,
        "nome_destinatario": nome_dest,
        "cnpj_destinatario": cnpj_dest,
        "tipo_nfe": tipo,
        "_arquivo_origem": origem,
    }


def _formatar_data(data_iso: str) -> str:
    """Converte data ISO 8601 (2024-01-15T12:00:00-03:00) para dd/mm/yyyy."""
    if not data_iso:
        return ""
    parte = data_iso[:10]  # pega YYYY-MM-DD
    try:
        from datetime import datetime
        dt = datetime.strptime(parte, "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    except ValueError:
        return parte
