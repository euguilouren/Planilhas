"""Testes para GeradorDashboard em dashboard_visual.py."""
import pandas as pd
import pytest
from dashboard_visual import GeradorDashboard


@pytest.fixture
def df_mensal():
    return pd.DataFrame({
        'Periodo':     ['01/2024', '02/2024', '03/2024'],
        'Receita_RS':  [10000.0, 12000.0, 8000.0],
        'NFs_Receita': [5, 6, 4],
        'Despesa_RS':  [7000.0, 9000.0, 6000.0],
        'NFs_Despesa': [3, 4, 2],
        'Resultado_RS':[3000.0, 3000.0, 2000.0],
        'Resultado_Pct':[30.0, 25.0, 25.0],
    })


@pytest.fixture
def df_dados():
    return pd.DataFrame({
        'NF':        ['001', '002', '003'],
        'Valor':     [10000.0, 12000.0, -7000.0],
        'Tipo':      ['RECEITA', 'RECEITA', 'DESPESA'],
        'Categoria': ['RECEITA', 'RECEITA', 'DESPESA OPERACIONAL'],
    })


class TestGeradorDashboard:

    def test_gerar_retorna_html(self, df_dados, df_mensal):
        html = GeradorDashboard.gerar('arquivo.xlsx', df_dados, df_fluxo_mensal=df_mensal)
        assert isinstance(html, str)
        assert '<!DOCTYPE html>' in html

    def test_kpi_receita_aparece(self, df_dados, df_mensal):
        html = GeradorDashboard.gerar('arquivo.xlsx', df_dados, df_fluxo_mensal=df_mensal)
        assert 'Receitas' in html
        assert 'NFs vendidas' in html

    def test_kpi_despesa_aparece(self, df_dados, df_mensal):
        html = GeradorDashboard.gerar('arquivo.xlsx', df_dados, df_fluxo_mensal=df_mensal)
        assert 'Despesas' in html
        assert 'NFs recebidas' in html

    def test_banner_sem_criticos(self, df_dados, df_mensal):
        html = GeradorDashboard.gerar('arquivo.xlsx', df_dados,
                                      df_fluxo_mensal=df_mensal, total_criticos=0)
        assert 'dados prontos para apresentação' in html

    def test_banner_com_criticos(self, df_dados, df_mensal):
        html = GeradorDashboard.gerar('arquivo.xlsx', df_dados,
                                      df_fluxo_mensal=df_mensal, total_criticos=3)
        assert '3 problema(s) crítico(s)' in html

    def test_chart_data_presente(self, df_dados, df_mensal):
        html = GeradorDashboard.gerar('arquivo.xlsx', df_dados, df_fluxo_mensal=df_mensal)
        assert 'chartFluxo' in html
        assert '01/2024' in html

    def test_sem_dados_mensal_ainda_retorna_html(self, df_dados):
        html = GeradorDashboard.gerar('arquivo.xlsx', df_dados)
        assert isinstance(html, str)
        assert 'Dashboard' in html

    def test_arquivo_nome_aparece(self, df_dados, df_mensal):
        html = GeradorDashboard.gerar('relatorio_jan.xlsx', df_dados,
                                      df_fluxo_mensal=df_mensal)
        assert 'relatorio_jan.xlsx' in html

    def test_dre_opcional_aparece(self, df_dados, df_mensal):
        df_dre = pd.DataFrame({
            'Linha_DRE': ['Receita Bruta', 'Lucro Líquido'],
            'Valor_RS':  [30000.0, 8000.0],
            'AV_%':      [100.0, 26.7],
        })
        html = GeradorDashboard.gerar('arquivo.xlsx', df_dados,
                                      df_fluxo_mensal=df_mensal, df_dre=df_dre)
        assert 'Receita Bruta' in html
        assert 'Lucro Líquido' in html

    def test_pareto_opcional_aparece(self, df_dados, df_mensal):
        df_pareto = pd.DataFrame({
            'Cliente':       ['Alfa', 'Beta'],
            'Total_RS':      [20000.0, 10000.0],
            'Percentual':    [66.7, 33.3],
            'Acumulado_%':   [66.7, 100.0],
            'Ranking':       [1, 2],
            'Classe_Pareto': ['A', 'B'],
        })
        html = GeradorDashboard.gerar('arquivo.xlsx', df_dados,
                                      df_fluxo_mensal=df_mensal, df_pareto=df_pareto)
        assert 'Alfa' in html
        assert 'Beta' in html
