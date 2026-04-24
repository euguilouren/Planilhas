"""Endpoints de upload de arquivos e consulta de jobs."""
import json
import os
import tempfile
from pathlib import Path
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from ..db import Job, Usuario, get_db
from ..deps import get_current_usuario, get_job_do_tenant
from ..models import JobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])

_EXTENSOES_OK = {".xlsx", ".xls", ".xlsm", ".csv", ".tsv"}
_MAX_BYTES = 50 * 1024 * 1024  # 50 MB


@router.post("/upload", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_arquivo(
    arquivo: UploadFile,
    usuario: Annotated[Usuario, Depends(get_current_usuario)],
    db: Session = Depends(get_db),
) -> Job:
    """Recebe arquivo, cria job e despacha para fila Celery."""
    nome = Path(arquivo.filename or "arquivo").name
    ext = Path(nome).suffix.lower()
    if ext not in _EXTENSOES_OK:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Extensão '{ext}' não suportada. Use: {', '.join(_EXTENSOES_OK)}",
        )

    conteudo = await arquivo.read()
    if len(conteudo) > _MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Arquivo muito grande. Máximo: {_MAX_BYTES // (1024*1024)} MB",
        )

    # Criar job no banco antes de despachar para fila
    job = Job(
        tenant_id=usuario.tenant_id,
        usuario_id=usuario.id,
        arquivo_nome=nome,
        status="pendente",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Salvar arquivo em disco temporário e despachar para Celery
    _despachar_job(job.id, nome, conteudo, usuario.tenant_id)

    return job


@router.get("/{job_id}", response_model=JobResponse)
def consultar_job(
    job: Annotated[Job, Depends(get_job_do_tenant)],
) -> Job:
    """Retorna status e resultado de um job."""
    return job


@router.get("/", response_model=List[JobResponse])
def listar_jobs(
    usuario: Annotated[Usuario, Depends(get_current_usuario)],
    db: Session = Depends(get_db),
    status_filtro: str = None,
) -> List[Job]:
    """Lista todos os jobs do tenant com filtro opcional de status."""
    q = db.query(Job).filter(Job.tenant_id == usuario.tenant_id)
    if status_filtro:
        q = q.filter(Job.status == status_filtro)
    return q.order_by(Job.criado_em.desc()).limit(100).all()


def _despachar_job(job_id: int, nome: str, conteudo: bytes, tenant_id: int) -> None:
    """Tenta despachar para Celery; se não disponível, processa inline (modo standalone)."""
    # Salvar arquivo temporário que o worker vai processar
    pasta = Path(os.getenv("PASTA_JOBS", "/tmp/toolkit_jobs"))
    pasta.mkdir(parents=True, exist_ok=True)
    caminho_temp = pasta / f"job_{job_id}_{nome}"
    caminho_temp.write_bytes(conteudo)

    try:
        from worker.tasks import processar_arquivo_task
        processar_arquivo_task.delay(job_id, str(caminho_temp), tenant_id)
    except Exception:
        # Celery/Redis não disponível — processar diretamente (modo dev/standalone)
        _processar_inline(job_id, str(caminho_temp), tenant_id)


def _processar_inline(job_id: int, caminho: str, tenant_id: int) -> None:
    """Processamento síncrono para ambientes sem Celery/Redis."""
    from sqlalchemy.orm import Session as _Session
    from ..db import SessionLocal, Job as _Job
    import traceback

    db: _Session = SessionLocal()
    try:
        job = db.query(_Job).filter(_Job.id == job_id).first()
        if not job:
            return
        job.status = "processando"
        db.commit()

        from motor_automatico import ProcessadorArquivo, carregar_config
        cfg = carregar_config()
        processador = ProcessadorArquivo(cfg)
        resultado = processador.processar(caminho)

        job.status = "concluido" if resultado.get("status") != "ERRO" else "erro"
        job.progresso_pct = 100
        job.resultado_json = json.dumps(resultado, ensure_ascii=False)
        if resultado.get("erro"):
            job.erro_mensagem = resultado["erro"]
        from datetime import datetime, timezone
        job.concluido_em = datetime.now(tz=timezone.utc)
        db.commit()
    except Exception as exc:
        job = db.query(_Job).filter(_Job.id == job_id).first()
        if job:
            job.status = "erro"
            job.erro_mensagem = str(exc)
            db.commit()
    finally:
        db.close()
