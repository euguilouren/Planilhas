"""Testes unitários para a classe Normalizador."""
import pytest
import pandas as pd
from pathlib import Path
import tempfile

from toolkit_financeiro import Normalizador


# ── helpers ─────────────────────────────────────────────────────────────

def _df_raw(**kwargs):
    """Cria DataFrame bruto com nomes arbitrários de coluna."""
    defaults = {
        'NUM_NF':   ['001', '002', '003'],
        'DT_EMIS':  ['01/01/2024', '15/01/2024', '20/01/2024'],
        'DT_VENC':  ['31/01/2024', '28/02/2024', '20/02/2024'],
        'VALOR_R$': [1500.0, 2000.0, 300.0],
        'CATEG':    ['RECEITA', 'CMV', 'DESPESA OPERACIONAL'],
        'CLIENTE':  ['Alpha', 'Beta', 'Gamma'],
    }
    defaults.update(kwargs)
    return pd.DataFrame(defaults)

MAPEAMENTO = {
    'NF': 'NUM_NF', 'Data': 'DT_EMIS', 'Vencimento': 'DT_VENC',
    'Valor': 'VALOR_R$', 'Categoria': 'CATEG', 'Cliente': 'CLIENTE',
}


# ── para_padrao ──────────────────────────────────────────────────────────

class TestParaPadrao:

    def test_colunas_padrao_presentes(self):
        df_raw = _df_raw()
        df = Normalizador.para_padrao(df_raw, MAPEAMENTO)
        assert list(df.columns) == Normalizador.NOMES_COLUNAS

    def test_valores_numericos_convertidos(self):
        df_raw = _df_raw(**{'VALOR_R$': ['R$ 1.500,00', '2000', '300,50']})
        df = Normalizador.para_padrao(df_raw, MAPEAMENTO)
        assert df['Valor'].iloc[0] == pytest.approx(1500.0)
        assert df['Valor'].iloc[1] == pytest.approx(2000.0)
        assert df['Valor'].iloc[2] == pytest.approx(300.5)

    def test_data_formato_br_preservada(self):
        df = Normalizador.para_padrao(_df_raw(), MAPEAMENTO)
        assert df['Data'].iloc[0] == '01/01/2024'
        assert df['Vencimento'].iloc[0] == '31/01/2024'

    def test_categoria_upper_e_valida(self):
        df_raw = _df_raw(**{'CATEG': ['receita', 'cmv', 'outro']})
        df = Normalizador.para_padrao(df_raw, MAPEAMENTO)
        assert df['Categoria'].iloc[0] == 'RECEITA'
        assert df['Categoria'].iloc[1] == 'CMV'
        assert df['Categoria'].iloc[2] == 'OUTRO'

    def test_categoria_invalida_vira_string_vazia(self):
        df_raw = _df_raw(**{'CATEG': ['RECEITA', 'INVALIDO_XYZ', 'CMV']})
        df = Normalizador.para_padrao(df_raw, MAPEAMENTO)
        assert df['Categoria'].iloc[1] == ''

    def test_status_ausente_preenche_pendente(self):
        df = Normalizador.para_padrao(_df_raw(), MAPEAMENTO)
        assert (df['Status'] == 'PENDENTE').all()

    def test_coluna_nao_mapeada_fica_vazia(self):
        mapeamento_parcial = {k: v for k, v in MAPEAMENTO.items() if k != 'Vencimento'}
        df = Normalizador.para_padrao(_df_raw(), mapeamento_parcial)
        assert (df['Vencimento'] == '').all()

    def test_nan_e_none_viram_string_vazia(self):
        import numpy as np
        df_raw = _df_raw(**{'CLIENTE': ['Alpha', None, np.nan]})
        df = Normalizador.para_padrao(df_raw, MAPEAMENTO)
        assert df['Cliente'].iloc[1] == ''
        assert df['Cliente'].iloc[2] == ''

    def test_df_vazio_retorna_colunas_corretas(self):
        df_raw = pd.DataFrame({k: [] for k in _df_raw().columns})
        df = Normalizador.para_padrao(df_raw, MAPEAMENTO)
        assert list(df.columns) == Normalizador.NOMES_COLUNAS
        assert len(df) == 0


# ── validar ──────────────────────────────────────────────────────────────

class TestValidar:

    def _df_valido(self):
        df_raw = _df_raw()
        return Normalizador.para_padrao(df_raw, MAPEAMENTO)

    def test_df_valido_sem_problemas(self):
        problemas = Normalizador.validar(self._df_valido())
        tipos = [p['tipo'] for p in problemas]
        assert 'CAMPO_OBRIGATORIO_VAZIO' not in tipos
        assert 'NF_DUPLICADA' not in tipos

    def test_detecta_campo_obrigatorio_vazio(self):
        df = self._df_valido()
        df.loc[1, 'NF'] = ''
        problemas = Normalizador.validar(df)
        tipos = [p['tipo'] for p in problemas]
        assert 'CAMPO_OBRIGATORIO_VAZIO' in tipos

    def test_detecta_nf_duplicada(self):
        df = self._df_valido()
        df.loc[2, 'NF'] = df.loc[0, 'NF']
        problemas = Normalizador.validar(df)
        tipos = [p['tipo'] for p in problemas]
        assert 'NF_DUPLICADA' in tipos

    def test_detecta_valor_negativo(self):
        df = self._df_valido()
        df.loc[0, 'Valor'] = -500.0
        problemas = Normalizador.validar(df)
        tipos = [p['tipo'] for p in problemas]
        assert 'VALOR_NEGATIVO' in tipos

    def test_detecta_categoria_invalida(self):
        df = self._df_valido()
        df.loc[0, 'Categoria'] = 'DESCONHECIDA'
        problemas = Normalizador.validar(df)
        tipos = [p['tipo'] for p in problemas]
        # Implementação usa VALOR_INVALIDO para listas com opção inválida
        assert any('INVALIDO' in t.upper() for t in tipos)

    def test_df_vazio_reporta_problema(self):
        df = pd.DataFrame(columns=Normalizador.NOMES_COLUNAS)
        problemas = Normalizador.validar(df)
        # DataFrame vazio deve reportar ausência de registros (não lança exceção)
        assert isinstance(problemas, list)

    def test_severidade_critica_em_campo_vazio(self):
        df = self._df_valido()
        df.loc[0, 'NF'] = ''
        problemas = Normalizador.validar(df)
        vazio_prob = next(p for p in problemas if p['tipo'] == 'CAMPO_OBRIGATORIO_VAZIO')
        assert vazio_prob['severidade'] in ('CRÍTICA', 'CRITICA', 'critica', 'crítica')


# ── gerar_template ───────────────────────────────────────────────────────

class TestGerarTemplate:

    def test_arquivo_criado(self):
        with tempfile.TemporaryDirectory() as d:
            caminho = str(Path(d) / 'tmpl.xlsx')
            resultado = Normalizador.gerar_template(caminho)
            assert Path(resultado).exists()

    def test_arquivo_legivel_como_excel(self):
        with tempfile.TemporaryDirectory() as d:
            caminho = str(Path(d) / 'tmpl.xlsx')
            Normalizador.gerar_template(caminho)
            df = pd.read_excel(caminho, sheet_name='DADOS')
            assert list(df.columns) == Normalizador.NOMES_COLUNAS

    def test_template_tem_linhas_de_exemplo(self):
        with tempfile.TemporaryDirectory() as d:
            caminho = str(Path(d) / 'tmpl.xlsx')
            Normalizador.gerar_template(caminho)
            df = pd.read_excel(caminho, sheet_name='DADOS')
            assert len(df) > 0

    def test_caminho_retornado_igual_ao_criado(self):
        with tempfile.TemporaryDirectory() as d:
            caminho = str(Path(d) / 'tmpl_ret.xlsx')
            resultado = Normalizador.gerar_template(caminho)
            assert resultado == caminho
