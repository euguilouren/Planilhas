"""Schemas Pydantic para request/response da API."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

# ── Auth ─────────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=6)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    sub: str  # email
    tenant_id: int
    role: str


# ── Tenants ──────────────────────────────────────────────────────────


class TenantCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=200)
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9\-]+$")


class TenantResponse(BaseModel):
    id: int
    nome: str
    slug: str
    ativo: bool
    criado_em: datetime

    model_config = {"from_attributes": True}


# ── Usuários ─────────────────────────────────────────────────────────


class UsuarioCreate(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=8)
    role: str = Field(default="analyst", pattern=r"^(admin|analyst|viewer)$")


class UsuarioResponse(BaseModel):
    id: int
    email: str
    role: str
    ativo: bool
    criado_em: datetime

    model_config = {"from_attributes": True}


# ── Jobs ─────────────────────────────────────────────────────────────


class JobResponse(BaseModel):
    id: int
    arquivo_nome: str
    status: str
    progresso_pct: int
    resultado_json: str | None = None
    erro_mensagem: str | None = None
    criado_em: datetime
    concluido_em: datetime | None = None

    model_config = {"from_attributes": True}
