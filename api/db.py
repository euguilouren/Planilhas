"""Banco de dados — SQLAlchemy + modelos multi-tenant."""
import os
from datetime import datetime
from typing import Generator

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Text,
    create_engine, func,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./toolkit.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(200), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    config_overrides = Column(Text, nullable=True)  # JSON com overrides de config.yaml
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, server_default=func.now())

    usuarios = relationship("Usuario", back_populates="tenant", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="tenant", cascade="all, delete-orphan")


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    email = Column(String(320), nullable=False, index=True)
    senha_hash = Column(String(256), nullable=False)
    role = Column(String(20), default="analyst")  # admin | analyst | viewer
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, server_default=func.now())

    tenant = relationship("Tenant", back_populates="usuarios")
    jobs = relationship("Job", back_populates="usuario")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    arquivo_nome = Column(String(500), nullable=False)
    status = Column(String(20), default="pendente")  # pendente | processando | concluido | erro
    progresso_pct = Column(Integer, default=0)
    resultado_json = Column(Text, nullable=True)  # JSON com caminhos dos arquivos gerados
    erro_mensagem = Column(Text, nullable=True)
    criado_em = Column(DateTime, server_default=func.now())
    concluido_em = Column(DateTime, nullable=True)

    tenant = relationship("Tenant", back_populates="jobs")
    usuario = relationship("Usuario", back_populates="jobs")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def criar_tabelas() -> None:
    Base.metadata.create_all(bind=engine)
