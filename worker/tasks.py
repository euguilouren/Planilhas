"""
Worker Celery — Toolkit Financeiro
=====================================
Processa arquivos financeiros de forma assíncrona.

Execução:
    celery -A worker.tasks worker --loglevel=info --concurrency=2

Variáveis de ambiente:
    REDIS_URL    — URL do Redis broker (padrão: redis://localhost:6379/0)
    DATABASE_URL — SQLAlchemy URL (padrão: sqlite:///./toolkit.db)
    PASTA_JOBS   — pasta com arquivos temporários dos jobs
"""
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from celery import Celery

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

app = Celery(
    "toolkit",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["worker.tasks"],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Sao_Paulo",
    enable_utc=True,
    task_soft_time_limit=300,   # 5 min — SIGTERM
    task_time_limit=360,        # 6 min — SIGKILL
    worker_max_tasks_per_child=50,  # reinicia worker após 50 tarefas (evita memory leak)
)


@app.task(bind=True, max_retries=2, default_retry_delay=10)
def processar_arquivo_task(self, job_id: int, caminho: str, tenant_id: int) -> dict:
    """Tarefa Celery: processa um arquivo financeiro e atualiza o Job no banco."""
    from api.db import SessionLocal, Job

    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error("Job %d não encontrado no banco", job_id)
            return {"erro": "job não encontrado"}

        job.status = "processando"
        job.progresso_pct = 5
        db.commit()

        logger.info("[job=%d] Iniciando processamento: %s", job_id, caminho)

        from motor_automatico import ProcessadorArquivo, carregar_config
        cfg = carregar_config()
        processador = ProcessadorArquivo(cfg)

        job.progresso_pct = 20
        db.commit()

        resultado = processador.processar(caminho)

        job.status = "concluido" if resultado.get("status") != "ERRO" else "erro"
        job.progresso_pct = 100
        job.resultado_json = json.dumps(resultado, ensure_ascii=False)
        job.concluido_em = datetime.now(tz=timezone.utc)
        if resultado.get("erro"):
            job.erro_mensagem = resultado["erro"]
        db.commit()

        # Remover arquivo temporário após processamento
        try:
            Path(caminho).unlink(missing_ok=True)
        except OSError:
            pass

        logger.info("[job=%d] Concluído. Status=%s", job_id, job.status)
        return resultado

    except Exception as exc:
        logger.error("[job=%d] Erro: %s", job_id, exc, exc_info=True)
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "erro"
            job.erro_mensagem = str(exc)
            db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()
