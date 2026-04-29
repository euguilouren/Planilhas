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


    def test_ler_ofx_sgml_retorna_dataframe(self, tmp_path):
        ofx = tmp_path / 'extrato.ofx'
        ofx.write_text(
            'OFXHEADER:100\nDATA:OFXSGML\n\n'
            '<OFX><BANKMSGSRSV1><STMTTRNRS><STMTRS><BANKTRANLIST>\n'
            '<STMTTRN>\n<TRNTYPE>CREDIT\n<DTPOSTED>20240115\n'
            '<TRNAMT>1500.00\n<FITID>TX001\n<MEMO>PAGAMENTO RECEBIDO\n</STMTTRN>\n'
            '<STMTTRN>\n<TRNTYPE>DEBIT\n<DTPOSTED>20240120\n'
            '<TRNAMT>-320.50\n<FITID>TX002\n<MEMO>CONTA DE LUZ\n</STMTTRN>\n'
            '</BANKTRANLIST></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>\n',
            encoding='utf-8',
        )
        df = Leitor.ler_ofx(str(ofx))
        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == ['Data', 'Vencimento', 'Valor', 'Descrição', 'ID', 'Tipo']
        assert len(df) == 2

    def test_ler_ofx_datas_convertidas(self, tmp_path):
        ofx = tmp_path / 'extrato.ofx'
        ofx.write_text(
            '<OFX><STMTTRNRS><STMTRS><BANKTRANLIST>\n'
            '<STMTTRN>\n<DTPOSTED>20240315000000[-3:BRT]\n<TRNAMT>100.00\n'
            '<FITID>X1\n<MEMO>TEV\n</STMTTRN>\n'
            '</BANKTRANLIST></STMTRS></STMTTRNRS></OFX>\n',
            encoding='utf-8',
        )
        df = Leitor.ler_ofx(str(ofx))
        assert df.iloc[0]['Data'] == '15/03/2024'

    def test_ler_ofx_valores_com_sinal(self, tmp_path):
        ofx = tmp_path / 'extrato.ofx'
        ofx.write_text(
            '<OFX><STMTTRNRS><STMTRS><BANKTRANLIST>\n'
            '<STMTTRN>\n<DTPOSTED>20240101\n<TRNAMT>500.00\n<FITID>A\n<MEMO>C\n</STMTTRN>\n'
            '<STMTTRN>\n<DTPOSTED>20240101\n<TRNAMT>-200.00\n<FITID>B\n<MEMO>D\n</STMTTRN>\n'
            '</BANKTRANLIST></STMTRS></STMTTRNRS></OFX>\n',
            encoding='utf-8',
        )
        df = Leitor.ler_ofx(str(ofx))
        assert df.iloc[0]['Valor'] == pytest.approx(500.0)
        assert df.iloc[1]['Valor'] == pytest.approx(-200.0)

    def test_ler_ofx_tipo_normalizado(self, tmp_path):
        ofx = tmp_path / 'extrato.ofx'
        ofx.write_text(
            '<OFX><STMTTRNRS><STMTRS><BANKTRANLIST>\n'
            '<STMTTRN>\n<DTPOSTED>20240101\n<TRNTYPE>CREDIT\n<TRNAMT>100\n<FITID>A\n<MEMO>M\n</STMTTRN>\n'
            '<STMTTRN>\n<DTPOSTED>20240101\n<TRNTYPE>DEBIT\n<TRNAMT>-50\n<FITID>B\n<MEMO>N\n</STMTTRN>\n'
            '</BANKTRANLIST></STMTRS></STMTTRNRS></OFX>\n',
            encoding='utf-8',
        )
        df = Leitor.ler_ofx(str(ofx))
        assert df.iloc[0]['Tipo'] == 'CRÉDITO'
        assert df.iloc[1]['Tipo'] == 'DÉBITO'

    def test_ler_ofx_sem_transacoes_levanta_erro(self, tmp_path):
        ofx = tmp_path / 'vazio.ofx'
        ofx.write_text('<OFX><BANKMSGSRSV1></BANKMSGSRSV1></OFX>\n', encoding='utf-8')
        with pytest.raises(ValueError, match='transação'):
            Leitor.ler_ofx(str(ofx))

    def test_ler_ofx_sem_bloco_ofx_levanta_erro(self, tmp_path):
        ofx = tmp_path / 'invalido.ofx'
        ofx.write_text('conteudo invalido sem tag ofx\n', encoding='utf-8')
        with pytest.raises(ValueError, match='OFX'):
            Leitor.ler_ofx(str(ofx))

    def test_ler_arquivo_despacha_ofx(self, tmp_path):
        ofx = tmp_path / 'extrato.ofx'
        ofx.write_text(
            '<OFX><STMTTRNRS><STMTRS><BANKTRANLIST>\n'
            '<STMTTRN>\n<DTPOSTED>20240101\n<TRNAMT>100\n<FITID>X\n<MEMO>M\n</STMTTRN>\n'
            '</BANKTRANLIST></STMTRS></STMTTRNRS></OFX>\n',
            encoding='utf-8',
        )
        resultado = Leitor.ler_arquivo(str(ofx))
        assert 'Extrato' in resultado['dados']
        assert resultado['diagnostico']['total_registros'] == 1


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

    def test_email_invalido_retorna_aviso(self):
        cfg = {
            'pastas': {'entrada': 'x', 'saida': 'y'},
            'colunas': {}, 'colunas_obrigatorias': [],
            'email': {
                'ativo': True,
                'smtp_servidor': 'smtp.gmail.com',
                'remetente': 'a@b.com',
                'destinatarios': ['nao-e-email', 'valido@exemplo.com'],
            },
        }
        avisos = validar_config(cfg)
        assert any('nao-e-email' in a for a in avisos)

    def test_emails_validos_sem_aviso(self):
        cfg = {
            'pastas': {'entrada': 'x', 'saida': 'y'},
            'colunas': {}, 'colunas_obrigatorias': [],
            'email': {
                'ativo': True,
                'smtp_servidor': 'smtp.gmail.com',
                'remetente': 'a@b.com',
                'destinatarios': ['usuario@empresa.com', 'outro@dominio.com.br'],
            },
        }
        avisos = validar_config(cfg)
        assert not any('Email inválido' in a for a in avisos)


# ── Edge cases de DataFrames vazios ───────────────────────────────

class TestEdgeCasesVazios:
    def test_relatorio_auditoria_df_vazio(self):
        df_resultado = Auditor.relatorio_auditoria([])
        assert isinstance(df_resultado, pd.DataFrame)
        assert len(df_resultado) == 0

    def test_pareto_df_vazio_retorna_dataframe(self):
        """pareto() com dados vazios deve retornar DataFrame (possivelmente vazio)
        — sem crash silencioso com TypeError/AttributeError."""
        df_vazio = pd.DataFrame(columns=['Cliente', 'Valor'])
        resultado = AnalistaComercial.pareto(df_vazio, 'Cliente', 'Valor')
        assert isinstance(resultado, pd.DataFrame)

    def test_aging_coluna_inexistente_levanta_ou_retorna_vazio(self):
        """calcular_aging() sem coluna de vencimento deve levantar KeyError/ValueError
        — nunca produzir resultado silenciosamente incorreto."""
        df = pd.DataFrame({'Valor': [100.0, 200.0]})
        with pytest.raises((KeyError, ValueError, TypeError)):
            AnalistaFinanceiro.calcular_aging(df, 'Vencimento', 'Valor')


class TestInconsistenciasTemporais:

    def test_data_futura_detectada(self):
        df = pd.DataFrame({'Data': ['01/01/2024', '01/01/2099']})
        resultado = Auditor.detectar_inconsistencias_temporais(df, 'Data')
        tipos = [r['tipo'] for r in resultado]
        assert 'DATA_FUTURA' in tipos

    def test_data_normal_sem_problemas(self):
        df = pd.DataFrame({'Data': ['01/01/2024', '15/03/2023']})
        resultado = Auditor.detectar_inconsistencias_temporais(df, 'Data')
        assert resultado == []

    def test_data_invertida_detectada(self):
        df = pd.DataFrame({
            'Emissao':    ['20/01/2024', '01/02/2024'],
            'Vencimento': ['10/01/2024', '28/02/2024'],  # primeira é invertida
        })
        resultado = Auditor.detectar_inconsistencias_temporais(
            df, 'Emissao', col_data2='Vencimento'
        )
        tipos = [r['tipo'] for r in resultado]
        assert 'DATA_INVERTIDA' in tipos

    def test_coluna_ausente_retorna_lista_vazia(self):
        df = pd.DataFrame({'Valor': [100.0, 200.0]})
        resultado = Auditor.detectar_inconsistencias_temporais(df, 'Data')
        assert resultado == []

    def test_resultado_tem_campos_esperados(self):
        df = pd.DataFrame({'Data': ['01/01/2099']})
        resultado = Auditor.detectar_inconsistencias_temporais(df, 'Data')
        assert len(resultado) == 1
        r = resultado[0]
        assert 'tipo' in r
        assert 'severidade' in r
        assert 'linha' in r
        assert 'coluna' in r


# ══════════════════════════════════════════════════════════════════
# Testes AnalistaFinanceiro.resumo_periodo()
# ══════════════════════════════════════════════════════════════════

class TestResumoPeriodo:

    @pytest.fixture
    def df_base(self):
        return pd.DataFrame({
            'NF':       ['001', '002', '003', '004'],
            'Data':     ['15/01/2024', '20/01/2024', '10/02/2024', '25/02/2024'],
            'Valor':    [5000.0, 3000.0, 8000.0, 2000.0],
            'Tipo':     ['RECEITA', 'DESPESA', 'RECEITA', 'DESPESA'],
        })

    def test_resumo_mensal_retorna_dataframe(self, df_base):
        from toolkit_financeiro import AnalistaFinanceiro
        result = AnalistaFinanceiro.resumo_periodo(df_base, freq='M')
        assert isinstance(result, pd.DataFrame)
        assert 'Receita_RS' in result.columns
        assert 'Despesa_RS' in result.columns
        assert 'Resultado_RS' in result.columns

    def test_resumo_mensal_agrupa_por_mes(self, df_base):
        from toolkit_financeiro import AnalistaFinanceiro
        result = AnalistaFinanceiro.resumo_periodo(df_base, freq='M')
        assert len(result) == 2  # jan/2024 e fev/2024

    def test_resumo_mensal_valores_corretos(self, df_base):
        from toolkit_financeiro import AnalistaFinanceiro
        result = AnalistaFinanceiro.resumo_periodo(df_base, freq='M')
        jan = result[result['Periodo'].str.startswith('01')].iloc[0]
        assert jan['Receita_RS'] == pytest.approx(5000.0)
        assert jan['Despesa_RS'] == pytest.approx(3000.0)
        assert jan['Resultado_RS'] == pytest.approx(2000.0)

    def test_resumo_anual_agrupa_por_ano(self, df_base):
        from toolkit_financeiro import AnalistaFinanceiro
        result = AnalistaFinanceiro.resumo_periodo(df_base, freq='A')
        assert len(result) == 1  # só 2024
        assert result.iloc[0]['Receita_RS'] == pytest.approx(13000.0)

    def test_resumo_sem_col_tipo_usa_fallback_por_valor(self):
        from toolkit_financeiro import AnalistaFinanceiro
        df = pd.DataFrame({
            'NF':   ['001', '002'],
            'Data': ['15/01/2024', '20/01/2024'],
            'Valor': [5000.0, -3000.0],
        })
        result = AnalistaFinanceiro.resumo_periodo(df, col_tipo='Tipo_Inexistente', freq='M')
        assert result.iloc[0]['Receita_RS'] == pytest.approx(5000.0)
        assert result.iloc[0]['Despesa_RS'] == pytest.approx(3000.0)

    def test_resumo_sem_datas_retorna_vazio(self):
        from toolkit_financeiro import AnalistaFinanceiro
        df = pd.DataFrame({'NF': ['001'], 'Valor': [100.0], 'Tipo': ['RECEITA']})
        result = AnalistaFinanceiro.resumo_periodo(df, freq='M')
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0


# ══════════════════════════════════════════════════════════════════
# Testes Normalizador — inferência de Tipo
# ══════════════════════════════════════════════════════════════════

class TestNormalizadorTipoInferido:

    def test_tipo_inferido_da_categoria_receita(self):
        from toolkit_financeiro import Normalizador
        df = pd.DataFrame({'NF': ['001'], 'Data': ['01/01/2024'],
                           'Vencimento': ['31/01/2024'], 'Valor': [100.0],
                           'Categoria': ['RECEITA'], 'Cliente': ['X']})
        result = Normalizador.para_padrao(df, {
            'NF': 'NF', 'Data': 'Data', 'Vencimento': 'Vencimento',
            'Valor': 'Valor', 'Categoria': 'Categoria', 'Cliente': 'Cliente'
        })
        assert 'Tipo' in result.columns
        assert result.iloc[0]['Tipo'] == 'RECEITA'

    def test_tipo_inferido_da_categoria_despesa(self):
        from toolkit_financeiro import Normalizador
        df = pd.DataFrame({'NF': ['001'], 'Data': ['01/01/2024'],
                           'Vencimento': ['31/01/2024'], 'Valor': [200.0],
                           'Categoria': ['DESPESA OPERACIONAL'], 'Cliente': ['Y']})
        result = Normalizador.para_padrao(df, {
            'NF': 'NF', 'Data': 'Data', 'Vencimento': 'Vencimento',
            'Valor': 'Valor', 'Categoria': 'Categoria', 'Cliente': 'Cliente'
        })
        assert result.iloc[0]['Tipo'] == 'DESPESA'

    def test_tipo_fallback_por_sinal_positivo(self):
        from toolkit_financeiro import Normalizador
        df = pd.DataFrame({'NF': ['001'], 'Data': ['01/01/2024'],
                           'Vencimento': ['31/01/2024'], 'Valor': [50.0],
                           'Categoria': ['OUTRO'], 'Cliente': ['Z']})
        result = Normalizador.para_padrao(df, {
            'NF': 'NF', 'Data': 'Data', 'Vencimento': 'Vencimento',
            'Valor': 'Valor', 'Categoria': 'Categoria', 'Cliente': 'Cliente'
        })
        assert result.iloc[0]['Tipo'] == 'RECEITA'

    def test_tipo_fallback_por_sinal_negativo(self):
        from toolkit_financeiro import Normalizador
        df = pd.DataFrame({'NF': ['001'], 'Data': ['01/01/2024'],
                           'Vencimento': ['31/01/2024'], 'Valor': [-100.0],
                           'Categoria': ['OUTRO'], 'Cliente': ['Z']})
        result = Normalizador.para_padrao(df, {
            'NF': 'NF', 'Data': 'Data', 'Vencimento': 'Vencimento',
            'Valor': 'Valor', 'Categoria': 'Categoria', 'Cliente': 'Cliente'
        })
        assert result.iloc[0]['Tipo'] == 'DESPESA'
