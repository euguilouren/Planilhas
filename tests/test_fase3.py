"""Testes para os módulos da Fase 3: exportadores, conciliação, forecast, fiscal."""
from datetime import date, timedelta

import pandas as pd
import pytest


# ── ExportadorPDF ─────────────────────────────────────────────────────

class TestExportadorPDF:
    def test_disponivel_retorna_bool(self):
        from exportadores.pdf import ExportadorPDF
        assert isinstance(ExportadorPDF.disponivel(), bool)

    def test_gerar_levanta_sem_backend(self, monkeypatch):
        from exportadores import pdf as mod
        monkeypatch.setattr(mod, "_tentar_weasyprint", lambda h, u: None)
        monkeypatch.setattr(mod, "_tentar_pdfkit", lambda h, u: None)
        from exportadores.pdf import ExportadorPDF
        with pytest.raises(RuntimeError, match="backend PDF"):
            ExportadorPDF.gerar("<html><body>teste</body></html>")

    def test_gerar_usa_primeiro_backend_disponivel(self, monkeypatch):
        from exportadores import pdf as mod
        monkeypatch.setattr(mod, "_tentar_weasyprint", lambda h, u: b"%PDF-mock")
        from exportadores.pdf import ExportadorPDF
        result = ExportadorPDF.gerar("<html>ok</html>")
        assert result == b"%PDF-mock"


# ── Conciliação ───────────────────────────────────────────────────────

@pytest.fixture
def df_nfs():
    return pd.DataFrame({
        "NF":    ["001", "002", "003"],
        "Data":  ["10/01/2024", "15/01/2024", "20/01/2024"],
        "Valor": [1000.0, 2000.0, 500.0],
    })


@pytest.fixture
def df_extrato():
    return pd.DataFrame({
        "Data":  ["10/01/2024", "15/01/2024"],
        "Valor": [1000.0, 1995.0],  # 001 exato, 002 divergente
        "Descricao": ["Pagamento 001", "Pagamento 002"],
    })


class TestConciliacao:
    def test_conciliado_valor_exato(self, df_nfs, df_extrato):
        from conciliacao.motor import conciliar
        resultado = conciliar(df_nfs, df_extrato)
        assert resultado.loc[0, "Status_Conciliacao"] == "CONCILIADO"

    def test_divergente_valor_proximo(self, df_nfs, df_extrato):
        from conciliacao.motor import conciliar
        resultado = conciliar(df_nfs, df_extrato)
        # NF 002 tem valor 2000 mas extrato tem 1995 — divergente
        assert resultado.loc[1, "Status_Conciliacao"] == "DIVERGENTE"

    def test_pendente_sem_lancamento(self, df_nfs, df_extrato):
        from conciliacao.motor import conciliar
        resultado = conciliar(df_nfs, df_extrato)
        assert resultado.loc[2, "Status_Conciliacao"] == "PENDENTE"

    def test_nfs_vazio_retorna_pendente(self):
        from conciliacao.motor import conciliar
        df_vazio = pd.DataFrame(columns=["NF", "Data", "Valor"])
        df_ext = pd.DataFrame({"Data": ["10/01/2024"], "Valor": [100.0]})
        resultado = conciliar(df_vazio, df_ext)
        assert len(resultado) == 0

    def test_extrato_vazio_tudo_pendente(self, df_nfs):
        from conciliacao.motor import conciliar
        df_ext = pd.DataFrame(columns=["Data", "Valor"])
        resultado = conciliar(df_nfs, df_ext)
        assert (resultado["Status_Conciliacao"] == "PENDENTE").all()

    def test_leitor_ofx_manual_parseia_simples(self, tmp_path):
        from conciliacao.motor import LeitorOFX
        ofx_content = """
<OFX>
<STMTTRN>
<DTPOSTED>20240115</DTPOSTED>
<TRNAMT>1000.00</TRNAMT>
<MEMO>Pagamento</MEMO>
<FITID>001</FITID>
</STMTTRN>
</OFX>
"""
        f = tmp_path / "extrato.ofx"
        f.write_text(ofx_content)
        df = LeitorOFX.ler(f)
        assert len(df) == 1
        assert float(df.iloc[0]["Valor"]) == 1000.0
        assert df.iloc[0]["Data"] == "15/01/2024"


# ── Forecast ─────────────────────────────────────────────────────────

@pytest.fixture
def df_historico():
    base = date(2024, 1, 1)
    linhas = []
    for i in range(90):
        d = base + timedelta(days=i)
        linhas.append({"Data": d.strftime("%d/%m/%Y"), "Valor": 333.0, "Tipo": "RECEITA"})
        linhas.append({"Data": d.strftime("%d/%m/%Y"), "Valor": -200.0, "Tipo": "DESPESA"})
    return pd.DataFrame(linhas)


class TestForecast:
    def test_projetar_retorna_df_com_colunas(self, df_historico):
        from forecast.engine import ForecastEngine
        df = ForecastEngine.projetar(df_historico, dias=[30, 60])
        assert "Horizonte_Dias" in df.columns
        assert "Saldo_Proj" in df.columns
        assert len(df) == 2

    def test_projetar_saldo_positivo_quando_receita_maior(self, df_historico):
        from forecast.engine import ForecastEngine
        df = ForecastEngine.projetar(df_historico, dias=[30])
        assert df.iloc[0]["Saldo_Proj"] > 0

    def test_projetar_diario_retorna_n_dias(self, df_historico):
        from forecast.engine import ForecastEngine
        df = ForecastEngine.projetar_diario(df_historico, dias=30)
        assert len(df) == 30

    def test_alertas_saldo_negativo(self):
        from forecast.engine import ForecastEngine
        df_proj = pd.DataFrame([
            {"Horizonte_Dias": 30, "Saldo_Proj": -500.0, "Alerta": "⚠️ SALDO NEGATIVO"},
        ])
        alertas = ForecastEngine.alertas(df_proj)
        assert len(alertas) == 1
        assert "SALDO NEGATIVO" in alertas[0] or "30" in alertas[0]

    def test_alertas_vazio_quando_positivo(self):
        from forecast.engine import ForecastEngine
        df_proj = pd.DataFrame([
            {"Horizonte_Dias": 30, "Saldo_Proj": 1000.0, "Alerta": "✅ OK"},
        ])
        alertas = ForecastEngine.alertas(df_proj)
        assert len(alertas) == 0

    def test_df_vazio_retorna_sem_erros(self):
        from forecast.engine import ForecastEngine
        df = pd.DataFrame(columns=["Data", "Valor", "Tipo"])
        resultado = ForecastEngine.projetar(df, dias=[30])
        assert isinstance(resultado, pd.DataFrame)


# ── Parser NF-e ───────────────────────────────────────────────────────

_NFE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
  <NFe>
    <infNFe Id="NFe35240101234567890123456789012345678901234567">
      <ide>
        <dhEmi>2024-01-15T12:00:00-03:00</dhEmi>
        <tpNF>1</tpNF>
        <natOp>Venda de Mercadorias</natOp>
      </ide>
      <emit>
        <xNome>Empresa Emitente LTDA</xNome>
      </emit>
      <dest>
        <xNome>Cliente Destinatario SA</xNome>
        <CNPJ>12345678000195</CNPJ>
      </dest>
      <total>
        <ICMSTot>
          <vNF>1500.00</vNF>
        </ICMSTot>
      </total>
    </infNFe>
  </NFe>
</nfeProc>
"""


class TestParserNFe:
    def test_ler_xml_retorna_dataframe(self, tmp_path):
        from fiscal.nfe_xml import ParserNFe
        f = tmp_path / "nota.xml"
        f.write_text(_NFE_XML, encoding="utf-8")
        df = ParserNFe.ler_xml(f)
        assert len(df) == 1

    def test_extrai_chave_acesso(self, tmp_path):
        from fiscal.nfe_xml import ParserNFe
        f = tmp_path / "nota.xml"
        f.write_text(_NFE_XML, encoding="utf-8")
        df = ParserNFe.ler_xml(f)
        assert "35240101234567890123456789012345678901234567" in df.iloc[0]["chave_acesso"]

    def test_extrai_valor_positivo_para_saida(self, tmp_path):
        from fiscal.nfe_xml import ParserNFe
        f = tmp_path / "nota.xml"
        f.write_text(_NFE_XML, encoding="utf-8")
        df = ParserNFe.ler_xml(f)
        assert float(df.iloc[0]["valor_total"]) == 1500.0

    def test_tipo_saida_mapeia_para_receita(self, tmp_path):
        from fiscal.nfe_xml import ParserNFe
        f = tmp_path / "nota.xml"
        f.write_text(_NFE_XML, encoding="utf-8")
        df = ParserNFe.ler_xml(f)
        assert df.iloc[0]["tipo_nfe"] == "RECEITA"

    def test_data_formatada_corretamente(self, tmp_path):
        from fiscal.nfe_xml import ParserNFe
        f = tmp_path / "nota.xml"
        f.write_text(_NFE_XML, encoding="utf-8")
        df = ParserNFe.ler_xml(f)
        assert df.iloc[0]["data_emissao"] == "15/01/2024"

    def test_ler_pasta_processa_multiplos(self, tmp_path):
        from fiscal.nfe_xml import ParserNFe
        for i in range(3):
            (tmp_path / f"nota{i}.xml").write_text(_NFE_XML, encoding="utf-8")
        df = ParserNFe.ler_pasta(tmp_path)
        assert len(df) == 3

    def test_para_schema_padrao_renomeia_colunas(self, tmp_path):
        from fiscal.nfe_xml import ParserNFe
        f = tmp_path / "nota.xml"
        f.write_text(_NFE_XML, encoding="utf-8")
        df = ParserNFe.ler_xml(f)
        df_std = ParserNFe.para_schema_padrao(df)
        assert "NF" in df_std.columns
        assert "Valor" in df_std.columns
        assert "Tipo" in df_std.columns

    def test_xml_invalido_retorna_dataframe_vazio(self, tmp_path):
        from fiscal.nfe_xml import ParserNFe
        f = tmp_path / "invalido.xml"
        f.write_text("não é xml", encoding="utf-8")
        df = ParserNFe.ler_xml(f)
        assert df.empty
