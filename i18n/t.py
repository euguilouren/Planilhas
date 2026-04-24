"""
Módulo de internacionalização (i18n) — lookup de strings com fallback para pt_BR.

Uso:
    from i18n.t import t
    label = t("kpi.receita_total")             # → "Receita Total" (pt_BR padrão)
    label = t("kpi.receita_total", lang="en_US")  # → "Total Revenue"
    label = t("status.problemas", n=5)         # → "5 problema(s) crítico(s) encontrado(s)."
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DIR = Path(__file__).parent
_cache: dict[str, dict[str, str]] = {}


def _carregar(lang: str) -> dict[str, str]:
    if lang not in _cache:
        caminho = _DIR / f"{lang}.json"
        if caminho.exists():
            _cache[lang] = json.loads(caminho.read_text(encoding="utf-8"))
        else:
            logger.warning("Arquivo de i18n não encontrado: %s", caminho)
            _cache[lang] = {}
    return _cache[lang]


def t(key: str, lang: str = "pt_BR", **kwargs: Any) -> str:
    """
    Retorna a string traduzida para *lang*, com fallback para pt_BR.
    Suporta placeholders {nome} via kwargs.
    """
    dicionario = _carregar(lang)
    texto = dicionario.get(key)
    if texto is None and lang != "pt_BR":
        texto = _carregar("pt_BR").get(key)
    if texto is None:
        logger.debug("Chave i18n não encontrada: %s [%s]", key, lang)
        return key  # retorna a chave como fallback final
    if kwargs:
        try:
            return texto.format(**kwargs)
        except (KeyError, ValueError):
            return texto
    return texto


def idiomas_disponiveis() -> list[str]:
    """Retorna lista de idiomas com arquivo JSON disponível."""
    return [p.stem for p in _DIR.glob("*.json")]
