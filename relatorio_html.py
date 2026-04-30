"""
Gerador de relatório HTML autônomo — sem dependências externas.
Produz um arquivo .html autocontido que abre em qualquer navegador.
"""

import html
import logging
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)


class GeradorHTML:
    """Gera relatório HTML completo a partir dos resultados do toolkit."""

    def __init__(self, config: dict):
        self.cfg = config
        self.tema = config.get('relatorio', {}).get('tema', {})
        self.COR_P   = self.tema.get('cor_primaria',    '#1A3556')
        self.COR_S   = self.tema.get('cor_secundaria',  '#C9A227')
        self.COR_DARK= self.tema.get('cor_dark',         '#0D1B2A')
        self.COR_OK  = self.tema.get('cor_ok',           '#D1FAE5')
        self.COR_OK_T= self.tema.get('cor_ok_text',      '#065F46')
        self.COR_AL  = self.tema.get('cor_alerta',       '#FEF3C7')
        self.COR_AL_T= self.tema.get('cor_alerta_text',  '#92400E')
        self.COR_CR  = self.tema.get('cor_critico',      '#FEE2E2')
        self.COR_CR_T= self.tema.get('cor_critico_text', '#991B1B')

    def gerar(
        self,
        arquivo_origem:  str,
        df_dados:        pd.DataFrame,
        df_auditoria:    pd.DataFrame,
        df_aging:        pd.DataFrame  = None,
        df_dre:          pd.DataFrame  = None,
        df_pareto:       pd.DataFrame  = None,
        df_ticket:       pd.DataFrame  = None,
        diagnostico:     dict          = None,
        df_fluxo_diario: pd.DataFrame  = None,
        df_fluxo_mensal: pd.DataFrame  = None,
        df_fluxo_anual:  pd.DataFrame  = None,
    ) -> str:
        """Gera relatório HTML autocontido a partir dos dados processados.

        Args:
            arquivo_origem: Nome do arquivo de origem (exibido no cabeçalho).
            df_dados: DataFrame principal com todos os registros.
            df_auditoria: DataFrame com os problemas detectados pela auditoria.
            df_aging: Aging de recebíveis (opcional).
            df_dre: Demonstrativo de Resultado (opcional).
            df_pareto: Análise Pareto por entidade (opcional).
            df_ticket: Ticket médio por entidade (opcional, não exibido ainda).
            diagnostico: Dict de diagnóstico retornado por :meth:`Leitor.ler_arquivo`.

        Returns:
            String HTML completa pronta para ser salva em disco.
        """
        logger.info("Gerando relatório HTML para: %s", arquivo_origem)
        empresa = self._esc(self.cfg.get('relatorio', {}).get('empresa', 'Empresa'))
        titulo  = self._esc(self.cfg.get('relatorio', {}).get('titulo',  'Relatório Financeiro'))
        agora   = datetime.now().strftime('%d/%m/%Y %H:%M')

        # KPIs principais
        total_registros = len(df_dados)
        col_valor = self.cfg.get('colunas', {}).get('valor', 'Valor')
        total_valor = pd.to_numeric(df_dados.get(col_valor, pd.Series(dtype=float)), errors='coerce').sum() if col_valor in df_dados.columns else 0
        total_criticos = len(df_auditoria[df_auditoria['Severidade'] == 'CRÍTICA']) if len(df_auditoria) else 0
        total_problemas = len(df_auditoria)

        html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{titulo} — {agora}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Inter', Arial, sans-serif; font-size: 14px; background: #EEF2F7; color: #0D1B2A; line-height: 1.6; -webkit-font-smoothing: antialiased; }}
  .header {{ background: linear-gradient(135deg, {self.COR_DARK} 0%, {self.COR_P} 100%); color: white; padding: 22px 36px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 20px rgba(13,27,42,.3); }}
  .header h1 {{ font-size: 20px; font-weight: 700; letter-spacing: -.3px; }}
  .header .empresa {{ font-size: 11px; opacity: .6; margin-bottom: 4px; font-weight: 500; text-transform: uppercase; letter-spacing: .5px; }}
  .header .meta {{ font-size: 11.5px; opacity: .7; text-align: right; font-variant-numeric: tabular-nums; }}
  .container {{ max-width: 1200px; margin: 28px auto; padding: 0 20px; }}
  .kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }}
  .kpi {{ background: white; border-radius: 12px; padding: 22px 20px; box-shadow: 0 4px 16px rgba(13,27,42,.08); border-left: 3px solid {self.COR_S}; }}
  .kpi.critico {{ border-left-color: #C0392B; }}
  .kpi.ok {{ border-left-color: #3A9E5C; }}
  .kpi .label {{ font-size: 10.5px; color: #8FA3BC; text-transform: uppercase; letter-spacing: .6px; font-weight: 600; }}
  .kpi .valor {{ font-size: 28px; font-weight: 700; color: {self.COR_P}; margin: 8px 0 4px; letter-spacing: -.5px; font-variant-numeric: tabular-nums; line-height: 1.1; }}
  .kpi.critico .valor {{ color: #C0392B; }}
  .kpi.ok .valor {{ color: #065F46; }}
  .kpi .sub {{ font-size: 11px; color: #9BA8B5; }}
  .card {{ background: white; border-radius: 12px; padding: 26px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(13,27,42,.06); border: 1px solid #DDE6F0; }}
  .card h2 {{ font-size: 14px; font-weight: 700; color: {self.COR_P}; margin-bottom: 18px; padding-bottom: 12px; border-bottom: 1px solid #DDE6F0; display: flex; align-items: center; gap: 8px; letter-spacing: -.1px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ background: {self.COR_DARK}; color: rgba(255,255,255,.85); padding: 10px 13px; text-align: left; font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: .4px; }}
  td {{ padding: 10px 13px; border-bottom: 1px solid #EEF2F7; font-variant-numeric: tabular-nums; }}
  tbody tr:last-child td {{ border-bottom: none; }}
  tbody tr:hover td {{ background: #F7FAFD; }}
  .badge {{ display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: 11px; font-weight: 600; }}
  .badge-critica {{ background: {self.COR_CR}; color: {self.COR_CR_T}; }}
  .badge-alta    {{ background: #FFF0E6; color: #7C2D12; }}
  .badge-media   {{ background: {self.COR_AL}; color: {self.COR_AL_T}; }}
  .badge-baixa   {{ background: {self.COR_OK}; color: {self.COR_OK_T}; }}
  .badge-ok      {{ background: {self.COR_OK}; color: {self.COR_OK_T}; }}
  .bar-wrap {{ background: #E8EEF6; border-radius: 999px; height: 7px; width: 100%; overflow: hidden; }}
  .bar {{ height: 7px; border-radius: 999px; }}
  .bar-ok      {{ background: #3A9E5C; }}
  .bar-atencao {{ background: #E8A020; }}
  .bar-critico {{ background: #C0392B; }}
  .dre-total {{ font-weight: 700; background: #F5F8FC; color: {self.COR_P}; }}
  .dre-sub   {{ color: #4A6080; padding-left: 26px !important; font-weight: 400; }}
  .footer {{ text-align: center; font-size: 11px; color: #9BA8B5; padding: 28px; border-top: 1px solid #DDE6F0; }}
  @media(max-width:768px){{ .kpis{{grid-template-columns:repeat(2,1fr);}} }}
</style>
</head>
<body>

<header class="header" role="banner">
  <div>
    <div class="empresa">{empresa}</div>
    <h1>{titulo}</h1>
  </div>
  <div class="meta" aria-label="Metadados do relatório">
    Arquivo: {self._esc(arquivo_origem)}<br>
    Gerado em: {agora}<br>
    {total_registros:,} registros processados
  </div>
</header>

<main class="container" role="main" aria-label="Relatório financeiro">
"""
        # ── KPIs ──────────────────────────────────────────────────
        kpi_critico_class = 'critico' if total_criticos > 0 else 'ok'
        kpi_prob_class    = 'critico' if total_criticos > 0 else ('ok' if total_problemas == 0 else '')
        html_content +=f"""
  <section class="kpis" role="region" aria-label="Indicadores principais">
    <div class="kpi" role="article" aria-label="Total de registros: {total_registros:,}">
      <div class="label">Total de Registros</div>
      <div class="valor" aria-live="polite">{total_registros:,}</div>
      <div class="sub">{arquivo_origem}</div>
    </div>
    <div class="kpi" role="article" aria-label="Total geral em reais: {total_valor:.0f}">
      <div class="label">Total Geral (R$)</div>
      <div class="valor" aria-live="polite">{self._fmt_brl(total_valor, 0)}</div>
      <div class="sub">soma da coluna {self._esc(col_valor)}</div>
    </div>
    <div class="kpi {kpi_critico_class}" role="article" aria-label="Problemas críticos: {total_criticos}">
      <div class="label">Problemas Críticos</div>
      <div class="valor" aria-live="assertive">{total_criticos}</div>
      <div class="sub">requerem ação imediata</div>
    </div>
    <div class="kpi {kpi_prob_class}" role="article" aria-label="Total de alertas: {total_problemas}">
      <div class="label">Total de Alertas</div>
      <div class="valor" aria-live="polite">{total_problemas}</div>
      <div class="sub">todos os níveis</div>
    </div>
  </section>
"""
        # ── Diagnóstico de Formato ─────────────────────────────────
        if diagnostico and diagnostico.get('problemas_formato'):
            html_content +=self._secao_diagnostico(diagnostico)

        # ── Auditoria ─────────────────────────────────────────────
        if len(df_auditoria) > 0:
            html_content +=self._secao_auditoria(df_auditoria)
        else:
            html_content +="""
  <section class="card" role="region" aria-label="Auditoria de dados">
    <h2>✓ Auditoria</h2>
    <p style="color:#065F46;font-weight:600;font-size:14px" role="status">Nenhum problema encontrado nos dados.</p>
  </section>
"""
        # ── Aging ─────────────────────────────────────────────────
        if df_aging is not None and len(df_aging):
            html_content +=self._secao_aging(df_aging)

        # ── Fluxo por Período ─────────────────────────────────────
        if any(df is not None and len(df) > 0
               for df in [df_fluxo_diario, df_fluxo_mensal, df_fluxo_anual]):
            html_content +=self._secao_fluxo(df_fluxo_diario, df_fluxo_mensal, df_fluxo_anual)

        # ── DRE ───────────────────────────────────────────────────
        if df_dre is not None and len(df_dre):
            html_content +=self._secao_dre(df_dre)

        # ── Pareto ────────────────────────────────────────────────
        if df_pareto is not None and len(df_pareto):
            html_content +=self._secao_pareto(df_pareto)

        html_content +=f"""
</main>
<footer class="footer" role="contentinfo">
  Relatório gerado automaticamente pelo Toolkit Financeiro &bull; {agora}
  <br>
  <span style="font-size:10px;opacity:0.7;">Powered by <strong>Luan Guilherme Lourenço</strong></span>
</footer>
</body></html>"""
        logger.info("Relatório HTML gerado (%d bytes)", len(html_content))
        return html_content

    # ── Seções privadas ───────────────────────────────────────────

    @staticmethod
    def _esc(val) -> str:
        if val is None:
            return ''
        return html.escape(str(val))

    @staticmethod
    def _fmt_brl(val, dec: int = 2) -> str:
        try:
            v = float(val)
            us = f"{abs(v):,.{dec}f}"
            br = us.replace(',', 'X').replace('.', ',').replace('X', '.')
            return f"R$ {'-' if v < 0 else ''}{br}"
        except (ValueError, TypeError):
            return '—'

    def _badge(self, sev) -> str:
        sev_str = str(sev or '').upper()
        cls = {'CRÍTICA': 'critica', 'ALTA': 'alta', 'MÉDIA': 'media',
               'BAIXA': 'baixa', 'OK': 'ok'}.get(sev_str, 'media')
        return f'<span class="badge badge-{cls}" role="status" aria-label="Severidade: {self._esc(sev_str)}">{self._esc(sev_str)}</span>'

    def gerar_pdf(self, html_str: str, caminho_pdf: str) -> bool:
        """Converte HTML gerado em PDF usando WeasyPrint.

        Args:
            html_str: String HTML retornada por :meth:`gerar`.
            caminho_pdf: Caminho de destino para o arquivo PDF.

        Returns:
            True se o PDF foi gerado, False se WeasyPrint não estiver instalado.
        """
        try:
            from weasyprint import HTML as WeasyprintHTML  # optional dependency
            WeasyprintHTML(string=html_str).write_pdf(caminho_pdf)
            logger.info("PDF gerado: %s", caminho_pdf)
            return True
        except ImportError:
            logger.warning(
                "WeasyPrint não instalado — PDF ignorado. "
                "Instale com: pip install weasyprint"
            )
            return False

    def _secao_diagnostico(self, diag: dict) -> str:
        rows = ''
        for p in diag['problemas_formato']:
            rows += (f"<tr><td>{self._esc(p.get('aba',''))}</td>"
                     f"<td>{self._esc(p.get('coluna',''))}</td>"
                     f"<td>{self._badge(p.get('severidade',''))}</td>"
                     f"<td>{self._esc(p.get('descricao',''))}</td></tr>")
        return f"""
  <section class="card" role="region" aria-label="Problemas de formato detectados">
    <h2>⚠ Problemas de Formato ({len(diag['problemas_formato'])})</h2>
    <table role="table" aria-label="Lista de problemas de formato">
      <thead><tr><th scope="col">Aba</th><th scope="col">Coluna</th><th scope="col">Severidade</th><th scope="col">Descrição</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </section>
"""

    def _secao_auditoria(self, df: pd.DataFrame) -> str:
        rows = ''
        for _, r in df.iterrows():
            sev    = str(r.get('Severidade', ''))
            raw    = r.get('Linha', '')
            if isinstance(raw, list):
                linha = ', '.join(str(x) for x in raw[:5])
            else:
                linha = str(raw)
            imp = r.get('Impacto R$', '')
            try:
                imp_val = float(imp)
                imp_str = self._fmt_brl(imp_val) if imp and str(imp) not in ('', '0', '0.0') else '—'
            except (ValueError, TypeError):
                imp_str = '—'
            rows += (f"<tr><td>{self._badge(sev)}</td>"
                     f"<td>{self._esc(r.get('Tipo',''))}</td>"
                     f"<td>{self._esc(linha)}</td>"
                     f"<td>{self._esc(r.get('Coluna',''))}</td>"
                     f"<td>{self._esc(r.get('Descrição',''))}</td>"
                     f"<td style='text-align:right'>{imp_str}</td></tr>")
        return f"""
  <section class="card" role="region" aria-label="Log de auditoria com {len(df)} problemas">
    <h2>🔍 Log de Auditoria ({len(df)} problemas)</h2>
    <table role="table" aria-label="Problemas de auditoria">
      <thead><tr>
        <th scope="col">Severidade</th><th scope="col">Tipo</th><th scope="col">Linha(s)</th>
        <th scope="col">Coluna</th><th scope="col">Descrição</th><th scope="col">Impacto R$</th>
      </tr></thead><tbody>{rows}</tbody>
    </table>
  </section>
"""

    def _secao_aging(self, df: pd.DataFrame) -> str:
        if 'Total_RS' not in df.columns or 'Faixa_Aging' not in df.columns:
            logger.warning("_secao_aging: colunas esperadas ausentes no DataFrame de aging.")
            return '<section class="card"><h2>📅 Aging de Recebíveis</h2><p style="color:#888;font-size:13px">Colunas de aging não encontradas no DataFrame (Total_RS / Faixa_Aging).</p></section>'
        total = df['Total_RS'].sum()
        rows = ''
        for _, r in df.iterrows():
            faixa = str(r['Faixa_Aging'])
            pct   = float(r.get('Percentual', 0))
            qtd   = int(r.get('Quantidade', 0))
            tot   = float(r.get('Total_RS', 0))
            if 'vencer' in faixa.lower():
                bar_cls = 'bar-ok'
            elif '1-30' in faixa or '31-60' in faixa:
                bar_cls = 'bar-atencao'
            else:
                bar_cls = 'bar-critico'
            bar = f'<div class="bar-wrap"><div class="bar {bar_cls}" style="width:{min(pct,100):.1f}%"></div></div>'
            rows += (f"<tr><td>{self._esc(faixa)}</td><td style='text-align:right'>{qtd}</td>"
                     f"<td style='text-align:right'>{self._fmt_brl(tot)}</td>"
                     f"<td style='text-align:right'>{pct:.1f}%</td>"
                     f"<td style='width:180px'>{bar}</td></tr>")
        return f"""
  <section class="card" role="region" aria-label="Aging de recebíveis">
    <h2>📅 Aging de Recebíveis — Total: {self._fmt_brl(total)}</h2>
    <table role="table" aria-label="Distribuição do aging por faixa de vencimento">
      <thead><tr>
        <th scope="col">Faixa</th><th scope="col" style="text-align:right">Qtd</th>
        <th scope="col" style="text-align:right">Valor</th>
        <th scope="col" style="text-align:right">%</th><th scope="col">Distribuição</th>
      </tr></thead><tbody>{rows}</tbody>
    </table>
  </section>
"""

    def _secao_dre(self, df: pd.DataFrame) -> str:
        rows = ''
        totais = {'(=) Receita Líquida', '(=) Lucro Bruto',
                  '(=) Resultado Operacional (EBIT)', '(=) EBIT (Resultado Operacional)',
                  '(=) Resultado antes IR/CSLL', '(=) Lucro Líquido'}
        for _, r in df.iterrows():
            linha = str(r.get('Linha_DRE', ''))
            valor = float(r.get('Valor_RS', 0))
            av    = f"{float(r['AV_%']):.1f}%" if 'AV_%' in r and pd.notna(r.get('AV_%')) else ''
            cls   = 'dre-total' if linha in totais else ('dre-sub' if (linha.startswith('(-)') or linha.startswith('(-/+)')) else '')
            cor   = '#C0392B' if valor < 0 and linha in totais else ''
            rows += (f"<tr class='{cls}'><td>{self._esc(linha)}</td>"
                     f"<td style='text-align:right;color:{cor}'>{self._fmt_brl(valor)}</td>"
                     f"<td style='text-align:right;color:#888'>{av}</td></tr>")
        return f"""
  <section class="card" role="region" aria-label="DRE — Demonstrativo de Resultado">
    <h2>📊 DRE — Demonstrativo de Resultado</h2>
    <table role="table" aria-label="Linhas do demonstrativo de resultado">
      <thead><tr>
        <th scope="col">Linha</th>
        <th scope="col" style="text-align:right">Valor (R$)</th>
        <th scope="col" style="text-align:right">AV%</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </section>
"""

    def _secao_pareto(self, df: pd.DataFrame) -> str:
        col_ent = df.columns[0]
        max_val = float(df['Total_RS'].max()) if len(df) else 1
        if not max_val or pd.isna(max_val):
            max_val = 1
        rows = ''
        for _, r in df.head(15).iterrows():
            pct_bar = min(float(r.get('Total_RS', 0)) / max_val * 100, 100)
            classe  = str(r.get('Classe_Pareto', ''))
            cor_cls = '#C9A227' if 'A' in classe else '#9BA8B5'
            bar = f'<div class="bar-wrap"><div class="bar" style="width:{pct_bar:.1f}%;background:{cor_cls}"></div></div>'
            rows += (f"<tr><td style='text-align:center'>{int(r.get('Ranking',0))}</td>"
                     f"<td>{self._esc(r[col_ent])}</td>"
                     f"<td style='text-align:right'>{self._fmt_brl(r.get('Total_RS', 0))}</td>"
                     f"<td style='text-align:right'>{float(r.get('Percentual',0)):.1f}%</td>"
                     f"<td style='text-align:right'>{float(r.get('Acumulado_%',0)):.1f}%</td>"
                     f"<td><span style='color:{cor_cls};font-weight:bold'>{classe}</span></td>"
                     f"<td style='width:120px'>{bar}</td></tr>")
        return f"""
  <section class="card" role="region" aria-label="Análise Pareto — top {min(15,len(df))} entidades">
    <h2>🏆 Análise Pareto — Top {min(15,len(df))} de {len(df)}</h2>
    <table role="table" aria-label="Ranking Pareto por entidade">
      <thead><tr>
        <th scope="col">#</th><th scope="col">{self._esc(col_ent)}</th>
        <th scope="col" style="text-align:right">Total R$</th>
        <th scope="col" style="text-align:right">%</th>
        <th scope="col" style="text-align:right">Acumulado</th>
        <th scope="col">Classe</th><th scope="col">Participação</th>
      </tr></thead><tbody>{rows}</tbody>
    </table>
  </section>
"""

    def _secao_fluxo(self, df_d, df_m, df_a) -> str:
        """Renderiza seção de fluxo de caixa por período (diário/mensal/anual)."""
        def _tabela(df, label_id):
            if df is None or len(df) == 0:
                return '<p style="color:#6B7280;font-size:13px">Nenhum dado disponível.</p>'
            tot_rec  = df['Receita_RS'].sum()
            tot_desp = df['Despesa_RS'].sum()
            tot_res  = df['Resultado_RS'].sum()
            rows = ''
            for _, r in df.iterrows():
                res = float(r['Resultado_RS'])
                cor = '#D1FAE5' if res >= 0 else '#FEE2E2'
                pct = float(r['Resultado_Pct'])
                pct_str = f'+{pct:.1f}%' if pct >= 0 else f'{pct:.1f}%'
                rows += (
                    f"<tr style='background:{cor}'>"
                    f"<td style='font-weight:600'>{self._esc(str(r['Periodo']))}</td>"
                    f"<td style='text-align:right;color:#065F46'>{self._fmt_brl(r['Receita_RS'])}</td>"
                    f"<td style='text-align:center'>{int(r['NFs_Receita'])}</td>"
                    f"<td style='text-align:right;color:#991B1B'>{self._fmt_brl(r['Despesa_RS'])}</td>"
                    f"<td style='text-align:center'>{int(r['NFs_Despesa'])}</td>"
                    f"<td style='text-align:right;font-weight:bold;color:{'#065F46' if res>=0 else '#991B1B'}'>"
                    f"{self._fmt_brl(res)}</td>"
                    f"<td style='text-align:center'>{pct_str}</td></tr>"
                )
            cor_tot = '#D1FAE5' if tot_res >= 0 else '#FEE2E2'
            rows += (
                f"<tr style='background:{cor_tot};font-weight:bold;border-top:2px solid #1A3556'>"
                f"<td>TOTAL</td>"
                f"<td style='text-align:right;color:#065F46'>{self._fmt_brl(tot_rec)}</td>"
                f"<td style='text-align:center'>—</td>"
                f"<td style='text-align:right;color:#991B1B'>{self._fmt_brl(tot_desp)}</td>"
                f"<td style='text-align:center'>—</td>"
                f"<td style='text-align:right;color:{'#065F46' if tot_res>=0 else '#991B1B'}'>"
                f"{self._fmt_brl(tot_res)}</td><td></td></tr>"
            )
            return f"""<div style="overflow-x:auto">
<table role="table">
  <thead><tr>
    <th scope="col">Período</th>
    <th scope="col" style="text-align:right">Receitas (R$)</th>
    <th scope="col" style="text-align:center">NFs Vendidas</th>
    <th scope="col" style="text-align:right">Despesas (R$)</th>
    <th scope="col" style="text-align:center">NFs Recebidas</th>
    <th scope="col" style="text-align:right">Resultado (R$)</th>
    <th scope="col" style="text-align:center">Resultado %</th>
  </tr></thead><tbody>{rows}</tbody>
</table></div>"""

        tab_d = _tabela(df_d, 'diario')
        tab_m = _tabela(df_m, 'mensal')
        tab_a = _tabela(df_a, 'anual')

        return f"""
  <section class="card" role="region" aria-label="Fluxo de Receitas e Despesas por Período">
    <h2>📅 Fluxo por Período — Receitas × Despesas</h2>
    <div style="display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap">
      <button onclick="(function(){{
        document.getElementById('tab-fluxo-d').style.display='none';
        document.getElementById('tab-fluxo-m').style.display='block';
        document.getElementById('tab-fluxo-a').style.display='none';
      }})()" style="padding:6px 16px;border:1px solid #1A3556;border-radius:6px;cursor:pointer;background:#fff">Mensal</button>
      <button onclick="(function(){{
        document.getElementById('tab-fluxo-d').style.display='block';
        document.getElementById('tab-fluxo-m').style.display='none';
        document.getElementById('tab-fluxo-a').style.display='none';
      }})()" style="padding:6px 16px;border:1px solid #1A3556;border-radius:6px;cursor:pointer;background:#fff">Diário</button>
      <button onclick="(function(){{
        document.getElementById('tab-fluxo-d').style.display='none';
        document.getElementById('tab-fluxo-m').style.display='none';
        document.getElementById('tab-fluxo-a').style.display='block';
      }})()" style="padding:6px 16px;border:1px solid #1A3556;border-radius:6px;cursor:pointer;background:#fff">Anual</button>
    </div>
    <div id="tab-fluxo-d" style="display:none">{tab_d}</div>
    <div id="tab-fluxo-m" style="display:block">{tab_m}</div>
    <div id="tab-fluxo-a" style="display:none">{tab_a}</div>
  </section>
"""
