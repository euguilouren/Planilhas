"""Testes para relatorio_html.py."""

import pandas as pd
import pytest

from relatorio_html import GeradorHTML


@pytest.fixture
def config_html():
    return {
        "relatorio": {
            "titulo": "Teste",
            "empresa": "Empresa Teste",
            "tema": {
                "cor_primaria": "#1F4E79",
                "cor_secundaria": "#2E75B6",
                "cor_ok": "#C6EFCE",
                "cor_alerta": "#FFEB9C",
                "cor_critico": "#FFC7CE",
            },
        },
        "colunas": {"valor": "Valor"},
    }


@pytest.fixture
def df_dados():
    return pd.DataFrame(
        {
            "NF": ["001"],
            "Valor": [100.0],
            "Data": ["01/01/2024"],
        }
    )


@pytest.fixture
def df_auditoria_vazia():
    return pd.DataFrame(columns=["Severidade", "Tipo", "Linha", "Coluna", "Descrição", "Impacto R$"])


class TestGeradorHTML:
    def test_gerar_retorna_string(self, config_html, df_dados, df_auditoria_vazia):
        g = GeradorHTML(config_html)
        html = g.gerar("teste.csv", df_dados, df_auditoria_vazia)
        assert isinstance(html, str)

    def test_gerar_tem_doctype(self, config_html, df_dados, df_auditoria_vazia):
        g = GeradorHTML(config_html)
        html = g.gerar("teste.csv", df_dados, df_auditoria_vazia)
        assert "<!DOCTYPE html>" in html

    def test_gerar_contem_titulo(self, config_html, df_dados, df_auditoria_vazia):
        g = GeradorHTML(config_html)
        html = g.gerar("teste.csv", df_dados, df_auditoria_vazia)
        assert "Teste" in html

    def test_gerar_contem_branding_luan(self, config_html, df_dados, df_auditoria_vazia):
        g = GeradorHTML(config_html)
        html = g.gerar("teste.csv", df_dados, df_auditoria_vazia)
        assert "Luan Guilherme" in html

    def test_gerar_contem_empresa(self, config_html, df_dados, df_auditoria_vazia):
        g = GeradorHTML(config_html)
        html = g.gerar("teste.csv", df_dados, df_auditoria_vazia)
        assert "Empresa Teste" in html

    def test_gerar_sem_aging_nao_quebra(self, config_html, df_dados, df_auditoria_vazia):
        g = GeradorHTML(config_html)
        html = g.gerar("teste.csv", df_dados, df_auditoria_vazia, df_aging=None, df_dre=None)
        assert isinstance(html, str)

    def test_gerar_com_dados_dre(self, config_html, df_dados, df_auditoria_vazia):
        df_dre = pd.DataFrame(
            {
                "Linha_DRE": ["(=) Receita Bruta", "(=) Lucro Líquido"],
                "Valor_RS": [1000.0, 100.0],
                "AV_%": [100.0, 10.0],
                "Status": ["OK", "OK"],
            }
        )
        g = GeradorHTML(config_html)
        html = g.gerar("teste.csv", df_dados, df_auditoria_vazia, df_dre=df_dre)
        assert "Receita Bruta" in html

    # ── Testes de segurança XSS ───────────────────────────────────

    def test_xss_empresa_escapada(self, df_dados, df_auditoria_vazia):
        cfg = {
            "relatorio": {"empresa": "<script>alert(1)</script>", "titulo": "T", "tema": {}},
            "colunas": {"valor": "Valor"},
        }
        g = GeradorHTML(cfg)
        resultado = g.gerar("arq.xlsx", df_dados, df_auditoria_vazia)
        assert "<script>alert(1)</script>" not in resultado
        assert "&lt;script&gt;" in resultado

    def test_xss_titulo_escapado(self, df_dados, df_auditoria_vazia):
        cfg = {
            "relatorio": {"empresa": "Emp", "titulo": '"><img src=x onerror=alert(1)>', "tema": {}},
            "colunas": {"valor": "Valor"},
        }
        g = GeradorHTML(cfg)
        resultado = g.gerar("arq.xlsx", df_dados, df_auditoria_vazia)
        assert "onerror=alert(1)>" not in resultado

    def test_xss_descricao_auditoria_escapada(self, config_html, df_dados):
        df_audit = pd.DataFrame(
            [
                {
                    "Severidade": "MÉDIA",
                    "Tipo": "<img src=x onerror=xss()>",
                    "Linha": 1,
                    "Coluna": "<b>Campo</b>",
                    "Descrição": "<script>xss()</script>",
                    "Impacto R$": 0,
                }
            ]
        )
        g = GeradorHTML(config_html)
        resultado = g.gerar("arq.xlsx", df_dados, df_audit)
        assert "<script>xss()</script>" not in resultado
        assert "<img src=x" not in resultado
        assert "<b>Campo</b>" not in resultado

    def test_xss_cliente_pareto_escapado(self, config_html, df_auditoria_vazia):
        df_dados = pd.DataFrame({"NF": ["001"], "Valor": [100.0]})
        # _secao_pareto usa df.columns[0] como coluna de entidade
        df_pareto = pd.DataFrame(
            {
                "Cliente": ["<b>Hack</b>"],
                "Total_RS": [100.0],
                "Percentual": [100.0],
                "Acumulado_%": [100.0],
                "Ranking": [1],
                "Classe_Pareto": ["A"],
            }
        )
        g = GeradorHTML(config_html)
        resultado = g.gerar("arq.xlsx", df_dados, df_auditoria_vazia, df_pareto=df_pareto)
        assert "<b>Hack</b>" not in resultado
        assert "&lt;b&gt;Hack&lt;/b&gt;" in resultado

    def test_auditoria_vazia_mostra_mensagem_ok(self, config_html, df_dados, df_auditoria_vazia):
        g = GeradorHTML(config_html)
        resultado = g.gerar("arq.xlsx", df_dados, df_auditoria_vazia)
        assert "Nenhum problema encontrado" in resultado
