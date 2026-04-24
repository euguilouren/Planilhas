"""Testes para a API REST — auth, tenants e jobs."""
import json
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.main import app
from api.db import Base, get_db, Tenant, Usuario
from api.routers.auth import hash_senha, _criar_token, _payload_usuario


# ── Banco SQLite em memória compartilhado (StaticPool) ────────────────

engine_test = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # todas as conexões compartilham a mesma conexão SQLite
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

Base.metadata.create_all(bind=engine_test)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def limpar_tabelas():
    """Limpa registros entre testes sem recriar o schema."""
    yield
    db = TestingSessionLocal()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
    finally:
        db.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def tenant_e_admin(db):
    """Cria tenant e usuário admin para uso nos testes."""
    tenant = Tenant(nome="Empresa Teste", slug="empresa-teste")
    db.add(tenant)
    db.flush()
    admin = Usuario(
        tenant_id=tenant.id,
        email="admin@empresa.com",
        senha_hash=hash_senha("senha123!"),
        role="admin",
    )
    analyst = Usuario(
        tenant_id=tenant.id,
        email="analyst@empresa.com",
        senha_hash=hash_senha("senha123!"),
        role="analyst",
    )
    db.add_all([admin, analyst])
    db.commit()
    return {"tenant": tenant, "admin": admin, "analyst": analyst}


def _token_para(usuario: Usuario) -> str:
    return _criar_token(_payload_usuario(usuario), timedelta(minutes=15))


# ── /health ───────────────────────────────────────────────────────────

class TestHealth:
    def test_health_retorna_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_health_tem_versao(self, client):
        resp = client.get("/health")
        assert "versao" in resp.json()


# ── /auth/login ───────────────────────────────────────────────────────

class TestLogin:
    def test_login_credenciais_validas(self, client, tenant_e_admin):
        resp = client.post("/auth/login", json={
            "email": "admin@empresa.com",
            "senha": "senha123!",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_senha_errada_retorna_401(self, client, tenant_e_admin):
        resp = client.post("/auth/login", json={
            "email": "admin@empresa.com",
            "senha": "senha_errada",
        })
        assert resp.status_code == 401

    def test_login_email_inexistente_retorna_401(self, client):
        resp = client.post("/auth/login", json={
            "email": "ninguem@nowhere.com",
            "senha": "qualquer",
        })
        assert resp.status_code == 401

    def test_token_permite_acessar_endpoint_protegido(self, client, tenant_e_admin):
        login = client.post("/auth/login", json={
            "email": "admin@empresa.com",
            "senha": "senha123!",
        })
        token = login.json()["access_token"]
        resp = client.get("/tenants/", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_sem_token_retorna_403(self, client):
        resp = client.get("/tenants/")
        assert resp.status_code in (401, 403)


# ── /tenants ──────────────────────────────────────────────────────────

class TestTenants:
    def test_admin_lista_tenants(self, client, tenant_e_admin):
        token = _token_para(tenant_e_admin["admin"])
        resp = client.get("/tenants/", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert len(resp.json()) >= 1
        assert resp.json()[0]["slug"] == "empresa-teste"

    def test_analyst_nao_pode_listar_tenants(self, client, tenant_e_admin):
        token = _token_para(tenant_e_admin["analyst"])
        resp = client.get("/tenants/", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_admin_cria_tenant(self, client, tenant_e_admin):
        token = _token_para(tenant_e_admin["admin"])
        resp = client.post("/tenants/", json={"nome": "Novo Cliente", "slug": "novo-cliente"},
                           headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 201
        assert resp.json()["slug"] == "novo-cliente"

    def test_slug_duplicado_retorna_409(self, client, tenant_e_admin):
        token = _token_para(tenant_e_admin["admin"])
        client.post("/tenants/", json={"nome": "Empresa X", "slug": "unico-slug"},
                    headers={"Authorization": f"Bearer {token}"})
        resp = client.post("/tenants/", json={"nome": "Empresa Y", "slug": "unico-slug"},
                           headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 409

    def test_admin_cria_usuario_no_tenant(self, client, tenant_e_admin):
        token = _token_para(tenant_e_admin["admin"])
        tenant_id = tenant_e_admin["tenant"].id
        resp = client.post(
            f"/tenants/{tenant_id}/usuarios",
            json={"email": "novo@empresa.com", "senha": "segura123!", "role": "viewer"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        assert resp.json()["role"] == "viewer"

    def test_email_duplicado_no_tenant_retorna_409(self, client, tenant_e_admin):
        token = _token_para(tenant_e_admin["admin"])
        tenant_id = tenant_e_admin["tenant"].id
        resp = client.post(
            f"/tenants/{tenant_id}/usuarios",
            json={"email": "admin@empresa.com", "senha": "outra123!", "role": "viewer"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 409


# ── /jobs ─────────────────────────────────────────────────────────────

class TestJobs:
    def test_listar_jobs_vazio_inicialmente(self, client, tenant_e_admin):
        token = _token_para(tenant_e_admin["analyst"])
        resp = client.get("/jobs/", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_upload_extensao_invalida_retorna_422(self, client, tenant_e_admin):
        token = _token_para(tenant_e_admin["analyst"])
        resp = client.post(
            "/jobs/upload",
            files={"arquivo": ("malware.exe", b"MZ\x90", "application/octet-stream")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    def test_upload_arquivo_muito_grande_retorna_413(self, client, tenant_e_admin, monkeypatch):
        import api.routers.uploads as mod
        monkeypatch.setattr(mod, "_MAX_BYTES", 10)
        token = _token_para(tenant_e_admin["analyst"])
        resp = client.post(
            "/jobs/upload",
            files={"arquivo": ("planilha.csv", b"NF,Valor\n001,100" * 5, "text/csv")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 413

    def test_job_inexistente_retorna_404(self, client, tenant_e_admin):
        token = _token_para(tenant_e_admin["analyst"])
        resp = client.get("/jobs/99999", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404


# ── Isolamento multi-tenant ───────────────────────────────────────────

class TestMultiTenancy:
    def test_tenants_nao_veeem_jobs_uns_dos_outros(self, client, db):
        """Dois tenants distintos não podem ver os jobs um do outro."""
        t1 = Tenant(nome="T1", slug="t1")
        t2 = Tenant(nome="T2", slug="t2")
        db.add_all([t1, t2])
        db.flush()

        u1 = Usuario(tenant_id=t1.id, email="u1@t1.com", senha_hash=hash_senha("s1234567!"), role="analyst")
        u2 = Usuario(tenant_id=t2.id, email="u2@t2.com", senha_hash=hash_senha("s1234567!"), role="analyst")
        db.add_all([u1, u2])
        db.commit()

        from api.db import Job as JobModel
        from datetime import datetime, timezone
        job_t1 = JobModel(tenant_id=t1.id, arquivo_nome="t1.xlsx", status="concluido",
                          concluido_em=datetime.now(tz=timezone.utc))
        db.add(job_t1)
        db.commit()

        token_u2 = _token_para(u2)
        resp = client.get(f"/jobs/{job_t1.id}", headers={"Authorization": f"Bearer {token_u2}"})
        assert resp.status_code == 404  # u2 não pode ver job do tenant 1
