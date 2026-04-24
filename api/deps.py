"""Dependências injetadas nos endpoints FastAPI."""
import os
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import _jwt
from .db import Job, Tenant, Usuario, get_db
from .models import TokenData

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "MUDE_EM_PRODUCAO_use_openssl_rand_hex_32")

bearer_scheme = HTTPBearer()


def _decodificar_token(token: str) -> TokenData:
    try:
        payload = _jwt.decode(token, SECRET_KEY)
        return TokenData(
            sub=payload["sub"],
            tenant_id=int(payload["tenant_id"]),
            role=payload["role"],
        )
    except (ValueError, KeyError) as exc:
        detail = "Token expirado" if "expirado" in str(exc) else "Token inválido"
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def get_token_data(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> TokenData:
    return _decodificar_token(credentials.credentials)


def get_current_usuario(
    token_data: Annotated[TokenData, Depends(get_token_data)],
    db: Annotated[Session, Depends(get_db)],
) -> Usuario:
    usuario = (
        db.query(Usuario)
        .filter(Usuario.email == token_data.sub, Usuario.ativo == True)  # noqa: E712
        .first()
    )
    if not usuario:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado")
    return usuario


def require_admin(usuario: Annotated[Usuario, Depends(get_current_usuario)]) -> Usuario:
    if usuario.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito a administradores")
    return usuario


def get_job_do_tenant(
    job_id: int,
    usuario: Annotated[Usuario, Depends(get_current_usuario)],
    db: Annotated[Session, Depends(get_db)],
) -> Job:
    """Retorna job apenas se pertencer ao tenant do usuário autenticado."""
    job = db.query(Job).filter(Job.id == job_id, Job.tenant_id == usuario.tenant_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job não encontrado")
    return job
