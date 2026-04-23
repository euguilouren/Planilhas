"""
Testes unitários para toolkit_financeiro.py

Execução:
    pytest tests/ -v
    pytest tests/ -v --cov=toolkit_financeiro --cov-report=term-missing
"""
import os
import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from toolkit_financeiro import (
    Status, Leitor, Auditor,
    AnalistaFinanceiro, AnalistaComercial,
    Util, Verificador, validar_config,
)


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def df_simples():
    return pd.DataFrame({
        'NF':        ['001', '002', '003', '001'],
        'Valor':     [100.0, 200.0, 50.0, 100.0],
        'Data':      ['01/01/2024', '15/01/2024', '20/01/2024', '01/01/2024'],
        'Categoria': ['RECEITA', 'CMV', 'DESPESA OPERACIONAL', 'RECEITA'],
        'Cliente':   ['Alfa', 'Beta', 'Alfa', 'Gamma'],
        'Vencimento': ['10/01/2024', '25/01/2024', '01/03/2024', '10/01/2024'],
    })


@pytest.fixture
def df_limpo():
    return pd.DataFrame({
        'NF':        ['001', '002', '003'],
        'Valor':     [100.0, 200.0, 50.0],
        'Data':      ['01/01/2024', '15/01/2024', '20/01/2024'],
        'Categoria': ['RECEITA', 'CMV', 'DESPESA OPERACIONAL'],
        'Cliente':   ['Alfa', 'Beta', 'Gamma'],
    })


@pytest.fixture
def config_completo():
    return {
        'pastas': {'entrada': 'pasta_entrada', 'saida': 'pasta_saida',
                   'log': 'pasta_saida/log.txt'},
        'colunas': {
            'valor': 'Valor', 'categoria': 'Categoria', 'data': 'Data',
            'vencimento': 'Vencimento', 'chave': 'NF', 'entidade': 'Cliente',
        },
        'colunas_obrigatorias': ['Valor', 'Data', 'NF'],
        'auditoria': {'outlier_desvios': 3.0, 'minimo_registros_analise': 5},
        'indicadores': {
            'liquidez_corrente_min': 1.0, 'liquidez_seca_min': 0.8,
            'margem_liquida_min': 5.0, 'endividamento_max': 100.0, 'roe_min': 15.0,
        },
        'email': {'ativo': False},
    }


# ── Status ────────────────────────────────────────────────────────

class TestStatus:
    def test_constantes_existem(self):
        assert Status.OK == 'OK'
        assert Status.CRITICA == 'CRÍTICA'
        assert Status.DIVERGENTE == 'DIVERGENTE'
        assert Status.DUPLICADO == 'DUPLICADO'
        assert Status.PARCIAL == 'PARCIAL'


# ── Leitor ────────────────────────────────────────────────────────

class TestLeitor:
    def test_arquivo_inexistente_levanta_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            Leitor.ler_arquivo('/nao/existe/arquivo.xlsx')

    def test_formato_nao_suportado_levanta_value_error(self, tmp_path):
        arq = tmp_path / 'teste.xyz'
        arq.write_text('conteudo')
        with pytest.raises(ValueError):
            Leitor.ler_arquivo(str(arq))

    def test_ler_csv_retorna_dados_e_diagnostico(self, tmp_path):
        csv = tmp_path / 'teste.csv'
        csv.write_text('NF,Valor,Data\n001,100,01/01/2024\n002,200,02/01/2024\n',
                       encoding='utf-8')
        resultado = Leitor.ler_arquivo(str(csv))
        assert 'dados' in resultado
        assert 'diagnostico' in resultado
        assert resultado['diagnostico']['total_registros'] == 2

    def test_ler_csv_cria_aba_dados(self, tmp_path):
        csv = tmp_path / 'teste.csv'
        csv.write_text('NF,Valor\n001,100\n', encoding='utf-8')
        resultado = Leitor.ler_arquivo(str(csv))
        assert 'Dados' in resultado['dados']

    def test_resumo_diagnostico_retorna_string(self):
        diag = {
            'arquivo': 'teste.csv', 'formato': '.csv',
            'total_registros': 10,
            'abas': [{'nome': 'Dados', 'linhas': 10, 'colunas': ['A', 'B'],
                      'nulos': {'A': 0, 'B': 1}, 'duplicatas': 0}],
            'problemas_formato': [],
        }
        resultado = Leitor.resumo_diagnostico(diag)
        assert isinstance(resultado, str)
        assert 'teste.csv' in resultado


# ── Auditor ───────────────────────────────────────────────────────

class TestAuditor:
    def test_detecta_duplicatas_por_chave(self, df_simples):
        dups = Auditor.detectar_duplicatas(df_simples, ['NF'], 'aba_teste')
        assert len(dups) == 2  # NF '001' aparece 2x

    def test_sem_duplicatas_retorna_vazio(self, df_limpo):
        dups = Auditor.detectar_duplicatas(df_limpo, ['NF'], 'aba_teste')
        assert len(dups) == 0

    def test_coluna_inexistente_retorna_vazio(self, df_simples):
        result = Auditor.detectar_duplicatas(df_simples, ['COLUNA_INEXISTENTE'])
        assert len(result) == 0

    def test_detecta_outlier_valor_extremo(self):
        df = pd.DataFrame({'Valor': [100.0, 100.0, 100.0, 100.0, 100.0, 9999.0]})
        outliers = Auditor.detectar_outliers(df, 'Valor', n_desvios=2.0)
        assert len(outliers) >= 1
        assert 9999.0 in outliers['Valor'].values

    def test_sem_variacao_nao_detecta_outlier(self):
        df = pd.DataFrame({'Valor': [100.0, 100.0, 100.0, 100.0]})
        outliers = Auditor.detectar_outliers(df, 'Valor')
        assert len(outliers) == 0

    def test_detecta_campos_vazios(self):
        df = pd.DataFrame({'NF': ['001', None, '003'], 'Valor': [1, 2, 3]})
        result = Auditor.detectar_campos_vazios(df, ['NF'], 'aba')
        assert len(result) >= 1

    def test_relatorio_auditoria_sem_inconsistencias(self):
        df = Auditor.relatorio_auditoria([])
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_relatorio_auditoria_retorna_dataframe(self):
        incons = [{
            'aba': 'Dados', 'linha': 2, 'coluna': 'NF',
            'tipo': 'DUPLICATA', 'severidade': Status.CRITICA,
            'valor': '001', 'descricao': 'Chave duplicada', 'impacto_rs': 100.0,
        }]
        df = Auditor.relatorio_auditoria(incons)
        assert isinstance(df, pd.DataFrame)
        assert 'Severidade' in df.columns
        assert len(df) == 1


# ── AnalistaFinanceiro ────────────────────────────────────────────

class TestAnalistaFinanceiro:
    def test_calcular_aging_retorna_dataframe(self, df_simples):
        resultado = AnalistaFinanceiro.calcular_aging(
            df_simples, 'Vencimento', 'Valor',
            data_ref=datetime(2024, 6, 1),
        )
        assert isinstance(resultado, pd.DataFrame)
        assert 'Faixa_Aging' in resultado.columns
        assert 'Total_RS' in resultado.columns

    def test_calcular_aging_soma_preservada(self, df_simples):
        resultado = AnalistaFinanceiro.calcular_aging(
            df_simples, 'Vencimento', 'Valor',
            data_ref=datetime(2024, 6, 1),
        )
        soma_aging = resultado['Total_RS'].sum()
        soma_original = pd.to_numeric(df_simples['Valor']).sum()
        assert abs(soma_aging - soma_original) < 0.01

    def test_calcular_aging_tem_percentual(self, df_simples):
        resultado = AnalistaFinanceiro.calcular_aging(
            df_simples, 'Vencimento', 'Valor',
            data_ref=datetime(2024, 6, 1),
        )
        assert 'Percentual' in resultado.columns
        assert abs(resultado['Percentual'].sum() - 100.0) < 1.0

    def test_construir_dre_retorna_colunas_esperadas(self, df_simples):
        dre = AnalistaFinanceiro.construir_dre(df_simples, 'Categoria', 'Valor')
        assert 'Linha_DRE' in dre.columns
        assert 'Valor_RS' in dre.columns

    def test_construir_dre_tem_lucro_liquido(self, df_simples):
        dre = AnalistaFinanceiro.construir_dre(df_simples, 'Categoria', 'Valor')
        assert '(=) Lucro Líquido' in dre['Linha_DRE'].values

    def test_construir_dre_tem_receita_bruta(self, df_simples):
        dre = AnalistaFinanceiro.construir_dre(df_simples, 'Categoria', 'Valor')
        assert any('Receita Bruta' in str(x) for x in dre['Linha_DRE'])

    def test_indicadores_saude_retorna_dataframe(self):
        df = AnalistaFinanceiro.indicadores_saude(
            ativo_circulante=200.0, passivo_circulante=100.0,
        )
        assert isinstance(df, pd.DataFrame)
        assert 'Indicador' in df.columns
        assert 'Valor' in df.columns
        assert 'Status' in df.columns

    def test_indicadores_saude_lc_saudavel(self):
        df = AnalistaFinanceiro.indicadores_saude(
            ativo_circulante=200.0, passivo_circulante=100.0,
        )
        lc = df[df['Indicador'] == 'Liquidez Corrente']
        assert len(lc) == 1
        assert lc.iloc[0]['Valor'] == pytest.approx(2.0)
        assert lc.iloc[0]['Status'] == 'SAUDÁVEL'

    def test_indicadores_saude_passivo_zero_sem_lc(self):
        df = AnalistaFinanceiro.indicadores_saude(
            ativo_circulante=200.0, passivo_circulante=0.0,
        )
        assert 'Liquidez Corrente' not in df['Indicador'].values

    def test_indicadores_saude_threshold_customizado(self):
        df = AnalistaFinanceiro.indicadores_saude(
            ativo_circulante=150.0, passivo_circulante=100.0,
            thresholds={'lc_min': 2.0},  # LC = 1.5, abaixo do limite 2.0
        )
        lc = df[df['Indicador'] == 'Liquidez Corrente']
        assert lc.iloc[0]['Status'] != 'SAUDÁVEL'


# ── AnalistaComercial ─────────────────────────────────────────────

class TestAnalistaComercial:
    def test_pareto_retorna_colunas_esperadas(self, df_simples):
        resultado = AnalistaComercial.pareto(df_simples, 'Cliente', 'Valor')
        assert 'Classe_Pareto' in resultado.columns
        assert 'Ranking' in resultado.columns
        assert 'Percentual' in resultado.columns

    def test_pareto_primeiro_e_maior(self, df_simples):
        resultado = AnalistaComercial.pareto(df_simples, 'Cliente', 'Valor')
        assert resultado.iloc[0]['Ranking'] == 1

    def test_pareto_soma_percentual_100(self, df_simples):
        resultado = AnalistaComercial.pareto(df_simples, 'Cliente', 'Valor')
        assert abs(resultado['Percentual'].sum() - 100.0) < 0.5

    def test_ticket_medio_sem_grupo(self, df_limpo):
        resultado = AnalistaComercial.ticket_medio(df_limpo, 'Valor')
        assert 'Ticket_Medio_RS' in resultado.columns
        soma = df_limpo['Valor'].sum()
        count = len(df_limpo)
        expected = soma / count
        assert resultado.iloc[0]['Ticket_Medio_RS'] == pytest.approx(expected, abs=0.01)

    def test_ticket_medio_com_grupo(self, df_simples):
        resultado = AnalistaComercial.ticket_medio(df_simples, 'Valor', 'Cliente')
        assert 'Cliente' in resultado.columns
        assert len(resultado) == 3  # Alfa, Beta, Gamma

    def test_realizado_vs_meta_meta_atingida(self):
        df_real = pd.DataFrame({'Regiao': ['Sul'], 'Vendas': [1000.0]})
        df_meta = pd.DataFrame({'Regiao': ['Sul'], 'Meta': [900.0]})
        resultado = AnalistaComercial.realizado_vs_meta(
            df_real, df_meta, 'Regiao', 'Vendas', 'Meta',
        )
        assert resultado.iloc[0]['Status'] == 'META ATINGIDA'

    def test_realizado_vs_meta_abaixo(self):
        df_real = pd.DataFrame({'Regiao': ['Norte'], 'Vendas': [500.0]})
        df_meta = pd.DataFrame({'Regiao': ['Norte'], 'Meta': [800.0]})
        resultado = AnalistaComercial.realizado_vs_meta(
            df_real, df_meta, 'Regiao', 'Vendas', 'Meta',
        )
        assert resultado.iloc[0]['Status'] == 'ABAIXO'

    def test_realizado_vs_meta_parcial(self):
        df_real = pd.DataFrame({'Regiao': ['Leste'], 'Vendas': [850.0]})
        df_meta = pd.DataFrame({'Regiao': ['Leste'], 'Meta': [1000.0]})
        resultado = AnalistaComercial.realizado_vs_meta(
            df_real, df_meta, 'Regiao', 'Vendas', 'Meta',
        )
        assert resultado.iloc[0]['Status'] == 'PARCIAL'


# ── Util ──────────────────────────────────────────────────────────

class TestUtil:
    def test_padronizar_texto_strip_e_upper(self):
        s = pd.Series(['  alfa ', 'BETA', 'gamma'])
        resultado = Util.padronizar_texto(s)
        assert resultado[0] == 'ALFA'
        assert resultado[1] == 'BETA'
        assert resultado[2] == 'GAMMA'

    def test_padronizar_texto_espacos_duplos(self):
        s = pd.Series(['Gamma  Delta'])
        resultado = Util.padronizar_texto(s)
        assert resultado[0] == 'GAMMA DELTA'

    def test_converter_moeda_br_reais(self):
        s = pd.Series(['R$ 1.234,56', '2.000,00'])
        resultado = Util.converter_moeda_br(s)
        assert resultado[0] == pytest.approx(1234.56)
        assert resultado[1] == pytest.approx(2000.00)

    def test_converter_moeda_br_invalido_vira_nan(self):
        s = pd.Series(['abc', ''])
        resultado = Util.converter_moeda_br(s)
        assert pd.isna(resultado[0])

    def test_normalizar_cnpj(self):
        s = pd.Series(['12.345.678/0001-90'])
        resultado = Util.normalizar_cnpj_cpf(s)
        assert resultado[0] == '12345678000190'

    def test_normalizar_cpf(self):
        s = pd.Series(['123.456.789-09'])
        resultado = Util.normalizar_cnpj_cpf(s)
        assert resultado[0] == '12345678909'

    def test_gerar_id_registro_estavel(self, df_limpo):
        ids1 = Util.gerar_id_registro(df_limpo, ['NF', 'Valor'])
        ids2 = Util.gerar_id_registro(df_limpo, ['NF', 'Valor'])
        assert ids1.equals(ids2)

    def test_gerar_id_registro_comprimento_12(self, df_limpo):
        ids = Util.gerar_id_registro(df_limpo, ['NF'])
        assert all(len(i) == 12 for i in ids)

    def test_detectar_entidades_similares_agrupa(self):
        s = pd.Series(['Alfa Ltda', 'ALFA LTDA', 'Beta SA'])
        grupos = Util.detectar_entidades_similares(s, threshold=0.8)
        assert len(grupos) >= 1
        nomes = [str(n).upper() for n in grupos[0]['nomes']]
        assert 'ALFA LTDA' in nomes

    def test_detectar_entidades_sem_similares(self):
        s = pd.Series(['Alfa', 'Beta', 'Gamma', 'Delta'])
        grupos = Util.detectar_entidades_similares(s, threshold=0.99)
        assert len(grupos) == 0


# ── Verificador ───────────────────────────────────────────────────

class TestVerificador:
    def test_integridade_ok_mesmos_dados(self, df_limpo):
        resultado = Verificador.verificar_integridade(df_limpo, df_limpo, 'Valor', 'teste')
        assert resultado['status'] == Status.OK

    def test_integridade_falha_registros_perdidos(self, df_limpo):
        df_menor = df_limpo.head(2)
        resultado = Verificador.verificar_integridade(df_limpo, df_menor, 'Valor', 'teste')
        assert resultado['status'] == 'FALHA'
        assert any(a['tipo'] == 'CONTAGEM_DIVERGENTE' for a in resultado['alertas'])

    def test_integridade_falha_soma_divergente(self, df_limpo):
        df_mod = df_limpo.copy()
        df_mod.loc[0, 'Valor'] = 9999.0
        resultado = Verificador.verificar_integridade(df_limpo, df_mod, 'Valor', 'teste')
        assert resultado['status'] == 'FALHA'
        assert any(a['tipo'] == 'SOMA_DIVERGENTE' for a in resultado['alertas'])

    def test_integridade_sem_coluna_valor_nao_quebra(self, df_limpo):
        resultado = Verificador.verificar_integridade(
            df_limpo, df_limpo, 'COLUNA_INEXISTENTE', 'teste',
        )
        assert resultado['status'] == Status.OK  # sem coluna de valor, apenas conta


# ── validar_config ─────────────────────────────────────────────────

class TestValidarConfig:
    def test_config_completo_sem_avisos(self, config_completo):
        avisos = validar_config(config_completo)
        assert avisos == []

    def test_config_sem_pastas_retorna_aviso(self):
        avisos = validar_config({})
        assert any('pastas' in a for a in avisos)

    def test_config_sem_colunas_retorna_aviso(self):
        avisos = validar_config({'pastas': {'entrada': 'x', 'saida': 'y'}})
        assert any('colunas' in a for a in avisos)

    def test_config_pastas_vazias_retorna_aviso(self):
        cfg = {
            'pastas': {'entrada': '', 'saida': 'y'},
            'colunas': {}, 'colunas_obrigatorias': [],
        }
        avisos = validar_config(cfg)
        assert any('entrada' in a for a in avisos)

    def test_email_ativo_sem_smtp_retorna_aviso(self):
        cfg = {
            'pastas': {'entrada': 'x', 'saida': 'y'},
            'colunas': {}, 'colunas_obrigatorias': [],
            'email': {'ativo': True, 'smtp_servidor': '', 'remetente': '',
                      'destinatarios': []},
        }
        avisos = validar_config(cfg)
        assert any('smtp_servidor' in a for a in avisos)

    def test_indicador_negativo_retorna_aviso(self):
        cfg = {
            'pastas': {'entrada': 'x', 'saida': 'y'},
            'colunas': {}, 'colunas_obrigatorias': [],
            'email': {'ativo': False},
            'indicadores': {'liquidez_corrente_min': -1.0},
        }
        avisos = validar_config(cfg)
        assert any('liquidez_corrente_min' in a for a in avisos)

    def test_porta_smtp_invalida_retorna_aviso(self):
        cfg = {
            'pastas': {'entrada': 'x', 'saida': 'y'},
            'colunas': {}, 'colunas_obrigatorias': [],
            'email': {
                'ativo': True,
                'smtp_servidor': 'smtp.gmail.com',
                'remetente': 'a@b.com',
                'destinatarios': ['c@d.com'],
                'smtp_porta': 99999,
            },
        }
        avisos = validar_config(cfg)
        assert any('smtp_porta' in a for a in avisos)
