"""Testes de integração end-to-end: CSV → HTML + Excel."""
import os
import tempfile
import textwrap
from pathlib import Path

import pytest
import pandas as pd

from toolkit_financeiro import Leitor, Auditor, AnalistaFinanceiro, AnalistaComercial, Status
from relatorio_html import GeradorHTML


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def config_padrao():
    return {
        'relatorio': {
            'titulo': 'Integração Teste',
            'empresa': 'Empresa Teste',
            'tema': {
                'cor_primaria': '#1A3556',
                'cor_secundaria': '#C9A227',
                'cor_dark': '#0D1B2A',
                'cor_ok': '#D1FAE5',
                'cor_ok_text': '#065F46',
                'cor_alerta': '#FEF3C7',
                'cor_alerta_text': '#92400E',
                'cor_critico': '#FEE2E2',
                'cor_critico_text': '#991B1B',
            },
        },
        'colunas': {
            'valor': 'Valor',
            'categoria': 'Categoria',
            'data': 'Data',
            'vencimento': 'Vencimento',
            'chave': 'NF',
            'entidade': 'Cliente',
        },
    }


@pytest.fixture
def csv_simples(tmp_path):
    """Cria CSV temporário com dados financeiros válidos."""
    conteudo = textwrap.dedent("""\
        NF,Valor,Data,Vencimento,Categoria,Cliente
        001,1000.00,01/01/2024,10/01/2024,RECEITA,Alfa
        002,2500.00,15/01/2024,25/01/2024,CMV,Beta
        003,500.00,20/01/2024,01/03/2024,DESPESA OPERACIONAL,Alfa
        004,3000.00,05/02/2024,15/02/2024,RECEITA,Gamma
        005,750.00,10/02/2024,20/02/2024,DESPESA OPERACIONAL,Beta
    """)
    arquivo = tmp_path / "dados_teste.csv"
    arquivo.write_text(conteudo, encoding='utf-8')
    return str(arquivo)


@pytest.fixture
def csv_com_duplicata(tmp_path):
    """CSV com NF duplicada para testar detecção de duplicatas."""
    conteudo = textwrap.dedent("""\
        NF,Valor,Data,Cliente
        001,100.00,01/01/2024,Alfa
        001,100.00,01/01/2024,Alfa
        002,200.00,02/01/2024,Beta
    """)
    arquivo = tmp_path / "dados_dup.csv"
    arquivo.write_text(conteudo, encoding='utf-8')
    return str(arquivo)


# ── Testes de pipeline completo ────────────────────────────────────

class TestPipelineCSVparaHTML:
    def test_leitura_csv_retorna_dados(self, csv_simples):
        resultado = Leitor.ler_arquivo(csv_simples)
        assert 'dados' in resultado
        assert 'diagnostico' in resultado
        df = list(resultado['dados'].values())[0]
        assert len(df) == 5
        assert 'NF' in df.columns
        assert 'Valor' in df.columns

    def test_auditoria_sem_problemas_em_dados_limpos(self, csv_simples):
        resultado = Leitor.ler_arquivo(csv_simples)
        df = list(resultado['dados'].values())[0]
        dups = Auditor.detectar_duplicatas(df, ['NF'])
        assert len(dups) == 0

    def test_auditoria_detecta_duplicatas(self, csv_com_duplicata):
        resultado = Leitor.ler_arquivo(csv_com_duplicata)
        df = list(resultado['dados'].values())[0]
        dups = Auditor.detectar_duplicatas(df, ['NF'])
        assert len(dups) == 2  # ambas as linhas NF=001 aparecem

    def test_html_gerado_e_string(self, csv_simples, config_padrao):
        resultado = Leitor.ler_arquivo(csv_simples)
        df = list(resultado['dados'].values())[0]
        df_audit = Auditor.relatorio_auditoria([])
        g = GeradorHTML(config_padrao)
        html = g.gerar('dados_teste.csv', df, df_audit,
                       diagnostico=resultado['diagnostico'])
        assert isinstance(html, str)
        assert '<!DOCTYPE html>' in html
        assert 'Integração Teste' in html

    def test_html_contém_registros(self, csv_simples, config_padrao):
        resultado = Leitor.ler_arquivo(csv_simples)
        df = list(resultado['dados'].values())[0]
        df_audit = Auditor.relatorio_auditoria([])
        g = GeradorHTML(config_padrao)
        html = g.gerar('dados_teste.csv', df, df_audit)
        # 5 registros processados deve aparecer no KPI
        assert '5' in html

    def test_html_gerado_em_disco(self, csv_simples, config_padrao, tmp_path):
        resultado = Leitor.ler_arquivo(csv_simples)
        df = list(resultado['dados'].values())[0]
        df_audit = Auditor.relatorio_auditoria([])
        g = GeradorHTML(config_padrao)
        html = g.gerar('dados_teste.csv', df, df_audit)
        caminho = tmp_path / "relatorio.html"
        caminho.write_text(html, encoding='utf-8')
        assert caminho.exists()
        assert caminho.stat().st_size > 1000

    def test_aging_calculado_corretamente(self, csv_simples):
        resultado = Leitor.ler_arquivo(csv_simples)
        df = list(resultado['dados'].values())[0]
        df_aging = AnalistaFinanceiro.calcular_aging(df, 'Vencimento', 'Valor')
        assert isinstance(df_aging, pd.DataFrame)
        assert 'Faixa_Aging' in df_aging.columns
        assert df_aging['Total_RS'].sum() > 0

    def test_pareto_calcula_classe_a(self, csv_simples):
        resultado = Leitor.ler_arquivo(csv_simples)
        df = list(resultado['dados'].values())[0]
        df_pareto = AnalistaComercial.pareto(df, 'Cliente', 'Valor')
        assert isinstance(df_pareto, pd.DataFrame)
        assert 'Classe_Pareto' in df_pareto.columns
        assert any('A' in str(c) for c in df_pareto['Classe_Pareto'].values)

    def test_pipeline_com_aging_e_pareto_no_html(self, csv_simples, config_padrao):
        resultado = Leitor.ler_arquivo(csv_simples)
        df = list(resultado['dados'].values())[0]
        df_audit = Auditor.relatorio_auditoria([])
        df_aging = AnalistaFinanceiro.calcular_aging(df, 'Vencimento', 'Valor')
        df_pareto = AnalistaComercial.pareto(df, 'Cliente', 'Valor')
        g = GeradorHTML(config_padrao)
        html = g.gerar('dados_teste.csv', df, df_audit,
                       df_aging=df_aging, df_pareto=df_pareto)
        assert 'Aging' in html
        assert 'Pareto' in html


class TestPipelineArquivoInexistente:
    def test_arquivo_inexistente_levanta_filenotfounderror(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            Leitor.ler_arquivo(str(tmp_path / "nao_existe.csv"))

    def test_extensao_invalida_levanta_valueerror(self, tmp_path):
        arq = tmp_path / "dados.txt"
        arq.write_text("a,b,c\n1,2,3")
        with pytest.raises((ValueError, RuntimeError)):
            Leitor.ler_arquivo(str(arq))


class TestIntegracaoToolkitPackage:
    """Verifica que o pacote toolkit/ re-exporta corretamente."""

    def test_importar_leitor_via_toolkit(self):
        from toolkit import Leitor as L  # noqa: F401
        assert L is not None

    def test_importar_auditor_via_submodulo(self):
        from toolkit.auditor import Auditor as A  # noqa: F401
        assert A is not None

    def test_importar_analista_via_submodulo(self):
        from toolkit.analista import AnalistaFinanceiro as AF  # noqa: F401
        assert AF is not None

    def test_version_disponivel(self):
        from toolkit import __version__
        assert __version__ >= "1.2.0"
