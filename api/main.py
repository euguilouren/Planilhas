"""
API REST — Toolkit Financeiro
================================
Execução:
    uvicorn api.main:app --reload
    uvicorn api.main:app --host 0.0.0.0 --port 8000

Variáveis de ambiente:
    JWT_SECRET_KEY   — chave secreta para tokens (obrigatório em produção)
    DATABASE_URL     — SQLAlchemy URL (padrão: sqlite:///./toolkit.db)
    REDIS_URL        — URL do Redis (padrão: redis://localhost:6379/0)
    PASTA_JOBS       — pasta para arquivos temporários de jobs
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import criar_tabelas
from .routers import auth, health, tenants, uploads


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    criar_tabelas()
    yield


app = FastAPI(
    title="Toolkit Financeiro API",
    description="API REST para processamento automatizado de planilhas financeiras.",
    version="1.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restringir em produção com ALLOWED_ORIGINS env var
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(tenants.router)
app.include_router(uploads.router)
