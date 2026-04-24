"""Testes para Conciliador — classe sem cobertura prévia."""

import pandas as pd
import pytest

from toolkit_financeiro import Conciliador, Status

# ── fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def df_extrato():
    return pd.DataFrame(
        {
            "NF": ["001", "002", "003"],
            "Valor": [100.0, 200.0, 50.0],
        }
    )


@pytest.fixture
def df_sistema():
    return pd.DataFrame(
        {
            "NF": ["001", "002", "004"],
            "Valor": [100.0, 205.0, 75.0],
        }
    )


# ── conciliar() ───────────────────────────────────────────────────────────


class TestConciliar:

    def test_match_exato_retorna_ok(self, df_extrato, df_sistema):
        result = Conciliador.conciliar(df_extrato, df_sistema, "NF", "Valor", "Valor")
        row = result[result["NF"] == "001"]
        assert len(row) == 1
        assert row.iloc[0]["Status_Conciliação"] == Status.OK

    def test_valores_diferentes_retorna_divergente(self, df_extrato, df_sistema):
        result = Conciliador.conciliar(df_extrato, df_sistema, "NF", "Valor", "Valor")
        row = result[result["NF"] == "002"]
        assert row.iloc[0]["Status_Conciliação"] == Status.DIVERGENTE

    def test_chave_apenas_em_fonte1_retorna_nao_encontrado(self, df_extrato, df_sistema):
        result = Conciliador.conciliar(
            df_extrato, df_sistema, "NF", "Valor", "Valor", nome_fonte1="Extrato", nome_fonte2="Sistema"
        )
        row = result[result["NF"] == "003"]
        assert "NÃO ENCONTRADO" in row.iloc[0]["Status_Conciliação"]
        assert "Sistema" in row.iloc[0]["Status_Conciliação"]

    def test_chave_apenas_em_fonte2_retorna_nao_encontrado(self, df_extrato, df_sistema):
        result = Conciliador.conciliar(
            df_extrato, df_sistema, "NF", "Valor", "Valor", nome_fonte1="Extrato", nome_fonte2="Sistema"
        )
        row = result[result["NF"] == "004"]
        assert "NÃO ENCONTRADO" in row.iloc[0]["Status_Conciliação"]
        assert "Extrato" in row.iloc[0]["Status_Conciliação"]

    def test_tolerancia_aceita_diferenca_pequena(self, df_extrato, df_sistema):
        # NF 002: extrato=200, sistema=205 → diferença=5 ≤ tolerância=10
        result = Conciliador.conciliar(df_extrato, df_sistema, "NF", "Valor", "Valor", tolerancia=10.0)
        row = result[result["NF"] == "002"]
        assert row.iloc[0]["Status_Conciliação"] == Status.OK

    def test_tolerancia_rejeita_diferenca_grande(self, df_extrato, df_sistema):
        # NF 002: diferença=5 > tolerância=3 → DIVERGENTE
        result = Conciliador.conciliar(df_extrato, df_sistema, "NF", "Valor", "Valor", tolerancia=3.0)
        row = result[result["NF"] == "002"]
        assert row.iloc[0]["Status_Conciliação"] == Status.DIVERGENTE

    def test_chave_duplicada_marca_como_duplicado(self):
        df1 = pd.DataFrame({"NF": ["001", "001"], "Valor": [100.0, 100.0]})
        df2 = pd.DataFrame({"NF": ["001"], "Valor": [100.0]})
        result = Conciliador.conciliar(df1, df2, "NF", "Valor", "Valor")
        statuses = result["Status_Conciliação"].tolist()
        assert any("DUPLICADO" in str(s) for s in statuses)

    def test_chave_composta_funciona(self):
        df1 = pd.DataFrame({"NF": ["001"], "Emp": ["A"], "Valor": [100.0]})
        df2 = pd.DataFrame({"NF": ["001"], "Emp": ["A"], "Valor": [100.0]})
        result = Conciliador.conciliar(df1, df2, ["NF", "Emp"], "Valor", "Valor")
        assert result.iloc[0]["Status_Conciliação"] == Status.OK

    def test_resultado_tem_coluna_diferenca(self, df_extrato, df_sistema):
        result = Conciliador.conciliar(df_extrato, df_sistema, "NF", "Valor", "Valor")
        assert "Diferença_R$" in result.columns
        assert "Diferença_%" in result.columns

    def test_resultado_outer_join_inclui_todas_chaves(self, df_extrato, df_sistema):
        # extrato tem 001,002,003 / sistema tem 001,002,004 → 4 NFs no resultado
        result = Conciliador.conciliar(df_extrato, df_sistema, "NF", "Valor", "Valor")
        assert len(result) == 4
        assert set(result["NF"].tolist()) == {"001", "002", "003", "004"}


# ── resumo_conciliacao() ──────────────────────────────────────────────────


class TestResumoConciliacao:

    def test_retorna_totalizadores_corretos(self, df_extrato, df_sistema):
        conciliado = Conciliador.conciliar(df_extrato, df_sistema, "NF", "Valor", "Valor")
        resumo = Conciliador.resumo_conciliacao(conciliado)
        assert resumo["total_registros"] == 4
        assert resumo["conciliados_ok"] == 1  # só NF 001 bate exatamente
        assert resumo["divergentes"] >= 1  # NF 002 diverge
        assert resumo["nao_encontrados"] == 2  # NF 003 e 004

    def test_percentual_ok_calculado(self, df_extrato, df_sistema):
        conciliado = Conciliador.conciliar(df_extrato, df_sistema, "NF", "Valor", "Valor")
        resumo = Conciliador.resumo_conciliacao(conciliado)
        # 1 OK de 4 = 25%
        assert resumo["percentual_ok"] == pytest.approx(25.0, abs=0.1)

    def test_soma_divergencias_positiva_quando_ha_divergencia(self, df_extrato, df_sistema):
        conciliado = Conciliador.conciliar(df_extrato, df_sistema, "NF", "Valor", "Valor")
        resumo = Conciliador.resumo_conciliacao(conciliado)
        assert resumo["soma_divergencias_rs"] > 0

    def test_sem_divergencias_soma_zero(self):
        df1 = pd.DataFrame({"NF": ["001", "002"], "Valor": [100.0, 200.0]})
        df2 = pd.DataFrame({"NF": ["001", "002"], "Valor": [100.0, 200.0]})
        conciliado = Conciliador.conciliar(df1, df2, "NF", "Valor", "Valor")
        resumo = Conciliador.resumo_conciliacao(conciliado)
        assert resumo["conciliados_ok"] == 2
        assert resumo["soma_divergencias_rs"] == 0.0
