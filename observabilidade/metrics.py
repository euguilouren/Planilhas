"""
Métricas Prometheus — Toolkit Financeiro.

Expõe métricas via endpoint GET /metrics (scrape do Prometheus).

Uso com FastAPI:
    from observabilidade.metrics import registrar_processamento, registrar_alerta
    registrar_processamento(tenant="cliente_x", status="concluido", duracao_s=2.3)
    registrar_alerta(tenant="cliente_x", categoria="DUPLICATA")

Uso standalone (inicia servidor de métricas na porta 9090):
    python -m observabilidade.metrics
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Generator

logger = logging.getLogger(__name__)


def _tentar_importar_prometheus():
    try:
        from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

        return Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
    except ImportError:
        return None


_prom = _tentar_importar_prometheus()

if _prom:
    Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST = _prom

    arquivos_processados = Counter(
        "toolkit_arquivos_processados_total",
        "Total de arquivos processados",
        ["tenant", "status"],
    )
    duracao_processamento = Histogram(
        "toolkit_processamento_duracao_segundos",
        "Duração do processamento por etapa",
        ["etapa"],
        buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0],
    )
    alertas_criticos = Counter(
        "toolkit_alertas_criticos_total",
        "Total de alertas críticos encontrados",
        ["tenant", "categoria"],
    )
    jobs_ativos = Gauge(
        "toolkit_jobs_ativos",
        "Número de jobs em processamento",
        ["tenant"],
    )
    _prometheus_disponivel = True
else:
    _prometheus_disponivel = False
    logger.info("prometheus_client não instalado — métricas desativadas")


def registrar_processamento(tenant: str, status: str, duracao_s: float = 0.0) -> None:
    if not _prometheus_disponivel:
        return
    arquivos_processados.labels(tenant=tenant, status=status).inc()
    if duracao_s > 0:
        duracao_processamento.labels(etapa="total").observe(duracao_s)


def registrar_alerta(tenant: str, categoria: str) -> None:
    if not _prometheus_disponivel:
        return
    alertas_criticos.labels(tenant=tenant, categoria=categoria).inc()


def incrementar_jobs_ativos(tenant: str) -> None:
    if _prometheus_disponivel:
        jobs_ativos.labels(tenant=tenant).inc()


def decrementar_jobs_ativos(tenant: str) -> None:
    if _prometheus_disponivel:
        jobs_ativos.labels(tenant=tenant).dec()


@contextmanager
def medir_etapa(nome_etapa: str) -> Generator[None, None, None]:
    """Context manager para medir duração de uma etapa."""
    if not _prometheus_disponivel:
        yield
        return
    inicio = time.perf_counter()
    try:
        yield
    finally:
        duracao = time.perf_counter() - inicio
        duracao_processamento.labels(etapa=nome_etapa).observe(duracao)


def endpoint_metricas():
    """Retorna bytes e content-type para o endpoint /metrics do FastAPI."""
    if not _prometheus_disponivel:
        return b"# prometheus_client nao instalado\n", "text/plain"
    return generate_latest(), CONTENT_TYPE_LATEST


if __name__ == "__main__":
    try:
        from prometheus_client import start_http_server

        porta = 9090
        start_http_server(porta)
        print(f"Servidor de métricas iniciado na porta {porta}")
        import signal
        import sys

        signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
        while True:
            time.sleep(1)
    except ImportError:
        print("Instale prometheus_client: pip install prometheus-client")
