"""Testes para relatorio_html.py."""
import pytest
import pandas as pd
from relatorio_html import GeradorHTML


@pytest.fixture
def config_html():
    return {
        'relatorio': {
            'titulo': 'Teste',
            'empresa': 'Empresa Teste',
            'tema': {
                'cor_primaria': '#1F4E79',
                'cor_secundaria': '#2E75B6',
                'cor_ok': '#C6EFCE',
                'cor_alerta': '#FFEB9C',
                'cor_critico': '#FFC7CE',
            },
        },
        'colunas': {'valor': 'Valor'},
    }


@pytest.fixture
def df_dados():
    return pd.DataFrame({
        'NF': ['001'], 'Valor': [100.0], 'Data': ['01/01/2024'],
    })


@pytest.fixture
def df_auditoria_vazia():
    return pd.DataFrame(columns=['Severidade', 'Tipo', 'Linha',
                                  'Coluna', 'Descrição', 'Impacto R$'])


class TestGeradorHTML:
    def test_gerar_retorna_string(self, config_html, df_dados, df_auditoria_vazia):
        g = GeradorHTML(config_html)
        html = g.gerar('teste.csv', df_dados, df_auditoria_vazia)
        assert isinstance(html, str)

    def test_gerar_tem_doctype(self, config_html, df_dados, df_auditoria_vazia):
        g = GeradorHTML(config_html)
        html = g.gerar('teste.csv', df_dados, df_auditoria_vazia)
        assert '<!DOCTYPE html>' in html

    def test_gerar_contem_titulo(self, config_html, df_dados, df_auditoria_vazia):
        g = GeradorHTML(config_html)
        html = g.gerar('teste.csv', df_dados, df_auditoria_vazia)
        assert 'Teste' in html

    def test_gerar_contem_branding_luan(self, config_html, df_dados, df_auditoria_vazia):
        g = GeradorHTML(config_html)
        html = g.gerar('teste.csv', df_dados, df_auditoria_vazia)
        assert 'Luan Guilherme' in html

    def test_gerar_contem_empresa(self, config_html, df_dados, df_auditoria_vazia):
        g = GeradorHTML(config_html)
        html = g.gerar('teste.csv', df_dados, df_auditoria_vazia)
        assert 'Empresa Teste' in html

    def test_gerar_sem_aging_nao_quebra(self, config_html, df_dados, df_auditoria_vazia):
        g = GeradorHTML(config_html)
        html = g.gerar('teste.csv', df_dados, df_auditoria_vazia,
                       df_aging=None, df_dre=None)
        assert isinstance(html, str)

    def test_gerar_com_dados_dre(self, config_html, df_dados, df_auditoria_vazia):
        df_dre = pd.DataFrame({
            'Linha_DRE': ['(=) Receita Bruta', '(=) Lucro Líquido'],
            'Valor_RS': [1000.0, 100.0],
            'AV_%': [100.0, 10.0],
            'Status': ['OK', 'OK'],
        })
        g = GeradorHTML(config_html)
        html = g.gerar('teste.csv', df_dados, df_auditoria_vazia, df_dre=df_dre)
        assert 'Receita Bruta' in html
