"""
toolkit — pacote modular do Toolkit Financeiro.

Re-exporta todas as classes públicas para que tanto
    from toolkit_financeiro import Leitor
quanto
    from toolkit import Leitor
continuem funcionando.

Subpacotes disponíveis:
    toolkit.status      — Status, validar_config
    toolkit.leitor      — Leitor, Estilos
    toolkit.auditor     — Auditor, Conciliador
    toolkit.analista    — AnalistaFinanceiro, AnalistaComercial, Util
    toolkit.montador    — MontadorPlanilha, PrestadorContas
    toolkit.verificador — Verificador, PipelineFinanceiro
"""

from toolkit_financeiro import (  # noqa: F401
    __version__,
    __author__,
    Status,
    validar_config,
    Leitor,
    Estilos,
    Auditor,
    Conciliador,
    AnalistaFinanceiro,
    AnalistaComercial,
    Util,
    PrestadorContas,
    MontadorPlanilha,
    Verificador,
    PipelineFinanceiro,
)

__all__ = [
    "__version__", "__author__",
    "Status", "validar_config",
    "Leitor", "Estilos",
    "Auditor", "Conciliador",
    "AnalistaFinanceiro", "AnalistaComercial", "Util",
    "PrestadorContas", "MontadorPlanilha",
    "Verificador", "PipelineFinanceiro",
]
