"""Testes para Fases 4-6: conectores ERP, i18n, white-label, métricas."""

import json
from pathlib import Path

import pytest

# ── Conectores ERP — base ─────────────────────────────────────────────


class TestConectorBase:
    def test_omie_exige_credenciais(self):
        from conectores.omie import ConectorOmie

        with pytest.raises(ValueError, match="app_key"):
            ConectorOmie({})

    def test_conta_azul_exige_credenciais(self):
        from conectores.conta_azul import ConectorContaAzul

        with pytest.raises(ValueError, match="client_id"):
            ConectorContaAzul({})

    def test_totvs_exige_base_url(self):
        from conectores.totvs import ConectorTOTVS

        with pytest.raises(ValueError, match="base_url"):
            ConectorTOTVS({})

    def test_omie_instancia_com_config_valida(self):
        from conectores.omie import ConectorOmie

        c = ConectorOmie({"app_key": "k", "app_secret": "s"})
        assert c.nome == "Omie"

    def test_totvs_instancia_com_config_valida(self):
        from conectores.totvs import ConectorTOTVS

        c = ConectorTOTVS({"base_url": "http://x", "usuario": "u", "senha": "p"})
        assert c.nome == "TOTVS Protheus"

    def test_schema_padrao_adiciona_colunas_faltantes(self):
        from conectores.base import ConectorERP

        df = ConectorERP._schema_padrao([{"NF": "001", "Valor": 100.0}])
        assert "Categoria" in df.columns
        assert "Tipo" in df.columns

    def test_omie_retorna_df_vazio_em_erro_de_rede(self, monkeypatch):
        """Simula falha de rede e verifica que retorna DataFrame vazio."""
        import urllib.error
        from datetime import date

        from conectores import omie as mod

        def _falhar(*args, **kwargs):
            raise urllib.error.URLError("timeout")

        monkeypatch.setattr(mod.request, "urlopen", _falhar)
        c = mod.ConectorOmie({"app_key": "k", "app_secret": "s"})
        df = c.buscar_lancamentos(date(2024, 1, 1), date(2024, 1, 31))
        assert df.empty


# ── i18n ──────────────────────────────────────────────────────────────


class TestI18n:
    def test_t_retorna_string_pt_br(self):
        from i18n.t import t

        assert t("kpi.receita_total") == "Receita Total"

    def test_t_retorna_string_en_us(self):
        from i18n.t import t

        assert t("kpi.receita_total", lang="en_US") == "Total Revenue"

    def test_t_fallback_para_pt_br_quando_idioma_ausente(self):
        from i18n.t import t

        resultado = t("kpi.receita_total", lang="xx_XX")
        assert resultado == "Receita Total"

    def test_t_retorna_chave_quando_nao_encontrada(self):
        from i18n.t import t

        resultado = t("chave.inexistente.xyz")
        assert resultado == "chave.inexistente.xyz"

    def test_t_formata_placeholder(self):
        from i18n.t import t

        resultado = t("status.problemas", n=5)
        assert "5" in resultado

    def test_idiomas_disponiveis_inclui_pt_br_e_en(self):
        from i18n.t import idiomas_disponiveis

        idiomas = idiomas_disponiveis()
        assert "pt_BR" in idiomas
        assert "en_US" in idiomas

    def test_todas_as_chaves_pt_br_presentes_no_en_us(self):
        """Garante que nenhuma chave foi esquecida na tradução EN."""
        from i18n.t import _carregar

        pt = _carregar("pt_BR")
        en = _carregar("en_US")
        faltando = set(pt.keys()) - set(en.keys())
        assert not faltando, f"Chaves faltando em en_US: {faltando}"


# ── White-label / Temas ───────────────────────────────────────────────


class TestTemas:
    def test_schema_json_valido(self):
        schema_path = Path("temas/schema.json")
        assert schema_path.exists()
        schema = json.loads(schema_path.read_text())
        assert schema["type"] == "object"
        assert "nome_produto" in schema["properties"]
        assert "cor_primaria" in schema["properties"]

    def test_schema_tem_exemplo(self):
        schema = json.loads(Path("temas/schema.json").read_text())
        assert "examples" in schema
        exemplo = schema["examples"][0]
        assert "nome_produto" in exemplo
        assert exemplo["cor_primaria"].startswith("#")


# ── Observabilidade ───────────────────────────────────────────────────


class TestMetricas:
    def test_registrar_processamento_sem_prometheus_nao_levanta(self):
        from observabilidade.metrics import registrar_processamento

        registrar_processamento("tenant_x", "concluido", duracao_s=1.5)

    def test_registrar_alerta_sem_prometheus_nao_levanta(self):
        from observabilidade.metrics import registrar_alerta

        registrar_alerta("tenant_x", "DUPLICATA")

    def test_endpoint_metricas_retorna_bytes(self):
        from observabilidade.metrics import endpoint_metricas

        conteudo, content_type = endpoint_metricas()
        assert isinstance(conteudo, bytes)
        assert isinstance(content_type, str)

    def test_medir_etapa_context_manager(self):
        import time

        from observabilidade.metrics import medir_etapa

        with medir_etapa("leitura"):
            time.sleep(0.01)  # não levanta

    def test_incrementar_e_decrementar_jobs_nao_levanta(self):
        from observabilidade.metrics import decrementar_jobs_ativos, incrementar_jobs_ativos

        incrementar_jobs_ativos("tenant_x")
        decrementar_jobs_ativos("tenant_x")


# ── Kubernetes manifests ──────────────────────────────────────────────


class TestK8sManifests:
    def test_deployment_yaml_existe_e_tem_resources(self):
        import yaml

        content = Path("k8s/deployment.yaml").read_text()
        docs = list(yaml.safe_load_all(content))
        api = next(d for d in docs if d["metadata"]["name"] == "toolkit-api")
        container = api["spec"]["template"]["spec"]["containers"][0]
        assert "limits" in container["resources"]
        assert container["resources"]["limits"]["memory"] == "512Mi"

    def test_hpa_yaml_existe_e_tem_limites(self):
        import yaml

        content = Path("k8s/hpa.yaml").read_text()
        docs = list(yaml.safe_load_all(content))
        hpa = next(d for d in docs if d["metadata"]["name"] == "toolkit-api-hpa")
        assert hpa["spec"]["maxReplicas"] == 10
        assert hpa["spec"]["minReplicas"] == 2

    def test_ingress_yaml_tem_tls(self):
        import yaml

        content = Path("k8s/ingress.yaml").read_text()
        ingress = yaml.safe_load(content)
        assert "tls" in ingress["spec"]
