"""Endpoints de autenticação JWT."""

import os
import time
from datetime import timedelta

import bcrypt as _bcrypt_lib
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import _jwt
from ..db import Usuario, get_db
from ..deps import SECRET_KEY, _decodificar_token
from ..models import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


def _criar_token(payload: dict, expires_delta: timedelta) -> str:
    exp = time.time() + expires_delta.total_seconds()
    return _jwt.encode({**payload, "exp": exp}, SECRET_KEY)


def _payload_usuario(usuario: Usuario) -> dict:
    return {"sub": usuario.email, "tenant_id": usuario.tenant_id, "role": usuario.role}


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    usuario = db.query(Usuario).filter(Usuario.email == body.email, Usuario.ativo == True).first()  # noqa: E712
    if not usuario or not _bcrypt_lib.checkpw(body.senha.encode(), usuario.senha_hash.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
        )
    payload = _payload_usuario(usuario)
    return TokenResponse(
        access_token=_criar_token(payload, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)),
        refresh_token=_criar_token({**payload, "type": "refresh"}, timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: dict, db: Session = Depends(get_db)) -> TokenResponse:
    token = body.get("refresh_token", "")
    token_data = _decodificar_token(token)
    usuario = db.query(Usuario).filter(Usuario.email == token_data.sub, Usuario.ativo == True).first()  # noqa: E712
    if not usuario:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado")
    payload = _payload_usuario(usuario)
    return TokenResponse(
        access_token=_criar_token(payload, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)),
        refresh_token=_criar_token({**payload, "type": "refresh"}, timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)),
    )


def hash_senha(senha: str) -> str:
    return _bcrypt_lib.hashpw(senha.encode(), _bcrypt_lib.gensalt()).decode()
