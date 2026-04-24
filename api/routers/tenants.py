"""Endpoints de gestão de tenants (admin-only)."""
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db import Tenant, Usuario, get_db
from ..deps import require_admin
from ..models import TenantCreate, TenantResponse, UsuarioCreate, UsuarioResponse
from .auth import hash_senha

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("/", response_model=List[TenantResponse])
def listar_tenants(
    _admin: Annotated[Usuario, Depends(require_admin)],
    db: Session = Depends(get_db),
) -> List[Tenant]:
    return db.query(Tenant).filter(Tenant.ativo == True).all()  # noqa: E712


@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
def criar_tenant(
    body: TenantCreate,
    _admin: Annotated[Usuario, Depends(require_admin)],
    db: Session = Depends(get_db),
) -> Tenant:
    if db.query(Tenant).filter(Tenant.slug == body.slug).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug já existe")
    tenant = Tenant(nome=body.nome, slug=body.slug)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@router.post("/{tenant_id}/usuarios", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def criar_usuario(
    tenant_id: int,
    body: UsuarioCreate,
    _admin: Annotated[Usuario, Depends(require_admin)],
    db: Session = Depends(get_db),
) -> Usuario:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id, Tenant.ativo == True).first()  # noqa: E712
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant não encontrado")
    if db.query(Usuario).filter(Usuario.email == body.email, Usuario.tenant_id == tenant_id).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="E-mail já cadastrado neste tenant")
    usuario = Usuario(
        tenant_id=tenant_id,
        email=body.email,
        senha_hash=hash_senha(body.senha),
        role=body.role,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario
