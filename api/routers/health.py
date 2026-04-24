"""Health check endpoints para liveness e readiness probes."""
import os
from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import text

from ..db import engine

router = APIRouter(tags=["health"])

_VERSAO = "1.3.0"


@router.get("/health")
def health() -> dict:
    """Liveness probe — responde se o processo está vivo."""
    return {"status": "ok", "versao": _VERSAO, "timestamp": datetime.now(tz=timezone.utc).isoformat()}


@router.get("/readiness")
def readiness() -> dict:
    """Readiness probe — verifica conexões externas."""
    db_ok = _checar_db()
    redis_ok = _checar_redis()

    if not db_ok:
        from fastapi import Response
        return {"status": "degradado", "db": "erro", "redis": "ok" if redis_ok else "erro"}

    return {
        "status": "ok",
        "db": "ok" if db_ok else "erro",
        "redis": "ok" if redis_ok else "indisponivel",
        "versao": _VERSAO,
    }


def _checar_db() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _checar_redis() -> bool:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        import redis as redis_lib
        r = redis_lib.from_url(redis_url, socket_connect_timeout=1)
        r.ping()
        return True
    except Exception:
        return False
