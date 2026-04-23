"""
Gerador de relatório HTML autônomo — sem dependências externas.
Produz um arquivo .html autocontido que abre em qualquer navegador.
"""

import logging
from datetime import datetime

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class GeradorHTML:
    """Gera relatório HTML completo a partir dos resultados do toolkit."""

    def __init__(self, config: dict):
        self.cfg = config
        self.tema = config.get('relatorio', {}).get('tema', {})
        self.COR_P  = self.tema.get('cor_primaria',   '#1F4E79')
        self.COR_S  = self.tema.get('cor_secundaria', '#2E75B6')
        self.COR_OK = self.tema.get('cor_ok',         '#C6EFCE')
        self.COR_AL = self.tema.get('cor_alerta',     '#FFEB9C')
        self.COR_CR = self.tema.get('cor_critico',    '#FFC7CE')

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
    ) -> str:
        """Retorna string HTML completa do relatório."""
        logger.info("Gerando relatório HTML para: %s", arquivo_origem)
        empresa = self.cfg.get('relatorio', {}).get('empresa', 'Empresa')
        titulo  = self.cfg.get('relatorio', {}).get('titulo',  'Relatório Financeiro')
        agora   = datetime.now().strftime('%d/%m/%Y %H:%M')

        # KPIs principais
        total_registros = len(df_dados)
        col_valor = self.cfg.get('colunas', {}).get('valor', 'Valor')
        total_valor = pd.to_numeric(df_dados.get(col_valor, pd.Series(dtype=float)), errors='coerce').sum() if col_valor in df_dados.columns else 0
        total_criticos = len(df_auditoria[df_auditoria['Severidade'] == 'CRÍTICA']) if len(df_auditoria) else 0
        total_problemas = len(df_auditoria)

        html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{titulo} — {agora}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Arial, sans-serif; font-size: 13px; background: #f4f6f9; color: #333; }}
  .header {{ background: {self.COR_P}; color: white; padding: 20px 32px; display: flex; justify-content: space-between; align-items: center; }}
  .header h1 {{ font-size: 22px; }}
  .header .meta {{ font-size: 11px; opacity: .8; text-align: right; }}
  .container {{ max-width: 1200px; margin: 24px auto; padding: 0 16px; }}
  .kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }}
  .kpi {{ background: white; border-radius: 8px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,.1); border-left: 4px solid {self.COR_S}; }}
  .kpi.critico {{ border-left-color: #C00000; }}
  .kpi.ok {{ border-left-color: #006100; }}
  .kpi .label {{ font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: .5px; }}
  .kpi .valor {{ font-size: 26px; font-weight: bold; color: {self.COR_P}; margin: 6px 0; }}
  .kpi.critico .valor {{ color: #C00000; }}
  .kpi.ok .valor {{ color: #006100; }}
  .kpi .sub {{ font-size: 11px; color: #aaa; }}
  .card {{ background: white; border-radius: 8px; padding: 24px; margin-bottom: 20px; box-shadow: 0 1px 4px rgba(0,0,0,.1); }}
  .card h2 {{ font-size: 15px; color: {self.COR_P}; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 2px solid {self.COR_P}; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
  th {{ background: {self.COR_P}; color: white; padding: 8px 10px; text-align: left; font-weight: 600; }}
  td {{ padding: 7px 10px; border-bottom: 1px solid #eee; }}
  tr:hover td {{ background: #f9f9f9; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; }}
  .badge-critica {{ background: {self.COR_CR}; color: #9C0006; }}
  .badge-alta    {{ background: #FCE4D6; color: #843C0C; }}
  .badge-media   {{ background: {self.COR_AL}; color: #9C5700; }}
  .badge-baixa   {{ background: {self.COR_OK}; color: #276221; }}
  .badge-ok      {{ background: {self.COR_OK}; color: #276221; }}
  .bar-wrap {{ background: #eee; border-radius: 4px; height: 14px; width: 100%; }}
  .bar {{ height: 14px; border-radius: 4px; }}
  .bar-ok      {{ background: #70AD47; }}
  .bar-atencao {{ background: #FFC000; }}
  .bar-critico {{ background: #C00000; }}
  .dre-total {{ font-weight: bold; background: #EBF3FB; }}
  .dre-sub   {{ color: #555; padding-left: 20px !important; }}
  .footer {{ text-align: center; font-size: 11px; color: #aaa; padding: 24px; }}
  @media(max-width:768px){{ .kpis{{grid-template-columns:repeat(2,1fr);}} }}
</style>
</head>
<body>

<div class="header">
  <div>
    <div style="font-size:12px;opacity:.7;margin-bottom:4px">{empresa}</div>
    <h1>{titulo}</h1>
  </div>
  <div class="meta">
    Arquivo: {arquivo_origem}<br>
    Gerado em: {agora}<br>
    {total_registros:,} registros processados
  </div>
</div>

<div class="container">
"""
        # ── KPIs ──────────────────────────────────────────────────
        kpi_critico_class = 'critico' if total_criticos > 0 else 'ok'
        kpi_prob_class    = 'critico' if total_criticos > 0 else ('ok' if total_problemas == 0 else '')
        html += f"""
  <div class="kpis">
    <div class="kpi">
      <div class="label">Total de Registros</div>
      <div class="valor">{total_registros:,}</div>
      <div class="sub">{arquivo_origem}</div>
    </div>
    <div class="kpi">
      <div class="label">Total Geral (R$)</div>
      <div class="valor">R$ {total_valor:,.0f}</div>
      <div class="sub">soma da coluna {col_valor}</div>
    </div>
    <div class="kpi {kpi_critico_class}">
      <div class="label">Problemas Críticos</div>
      <div class="valor">{total_criticos}</div>
      <div class="sub">requerem ação imediata</div>
    </div>
    <div class="kpi {kpi_prob_class}">
      <div class="label">Total de Alertas</div>
      <div class="valor">{total_problemas}</div>
      <div class="sub">todos os níveis</div>
    </div>
  </div>
"""
        # ── Diagnóstico de Formato ─────────────────────────────────
        if diagnostico and diagnostico.get('problemas_formato'):
            html += self._secao_diagnostico(diagnostico)

        # ── Auditoria ─────────────────────────────────────────────
        if len(df_auditoria) > 0:
            html += self._secao_auditoria(df_auditoria)
        else:
            html += """
  <div class="card">
    <h2>✓ Auditoria</h2>
    <p style="color:#006100;font-weight:bold">Nenhum problema encontrado nos dados.</p>
  </div>
"""
        # ── Aging ─────────────────────────────────────────────────
        if df_aging is not None and len(df_aging):
            html += self._secao_aging(df_aging)

        # ── DRE ───────────────────────────────────────────────────
        if df_dre is not None and len(df_dre):
            html += self._secao_dre(df_dre)

        # ── Pareto ────────────────────────────────────────────────
        if df_pareto is not None and len(df_pareto):
            html += self._secao_pareto(df_pareto)

        html += f"""
</div>
<div class="footer">
  Relatório gerado automaticamente pelo Toolkit Financeiro &bull; {agora}
  <br>
  <span style="font-size:10px;opacity:0.7;">Powered by <strong>Luan Guilherme Lourenço</strong></span>
</div>
</body></html>"""
        logger.info("Relatório HTML gerado (%d bytes)", len(html))
        return html

    # ── Seções privadas ───────────────────────────────────────────

    def _badge(self, sev: str) -> str:
        cls = {'CRÍTICA': 'critica', 'ALTA': 'alta', 'MÉDIA': 'media',
               'BAIXA': 'baixa', 'OK': 'ok'}.get(sev.upper(), 'media')
        return f'<span class="badge badge-{cls}">{sev}</span>'

    def _secao_diagnostico(self, diag: dict) -> str:
        rows = ''
        for p in diag['problemas_formato']:
            rows += f"<tr><td>{p.get('aba','')}</td><td>{p.get('coluna','')}</td><td>{self._badge(p.get('severidade',''))}</td><td>{p.get('descricao','')}</td></tr>"
        return f"""
  <div class="card">
    <h2>⚠ Problemas de Formato ({len(diag['problemas_formato'])})</h2>
    <table><thead><tr><th>Aba</th><th>Coluna</th><th>Severidade</th><th>Descrição</th></tr></thead>
    <tbody>{rows}</tbody></table>
  </div>
"""

    def _secao_auditoria(self, df: pd.DataFrame) -> str:
        rows = ''
        for _, r in df.iterrows():
            sev   = str(r.get('Severidade', ''))
            linha = str(r.get('Linha', ''))
            if isinstance(r.get('Linha'), list):
                linha = ', '.join(str(x) for x in r['Linha'][:5])
            imp = r.get('Impacto R$', '')
            imp_str = f"R$ {float(imp):,.2f}" if imp and str(imp) not in ('', '0', '0.0') else '—'
            rows += (f"<tr><td>{self._badge(sev)}</td>"
                     f"<td>{r.get('Tipo','')}</td>"
                     f"<td>{linha}</td>"
                     f"<td>{r.get('Coluna','')}</td>"
                     f"<td>{r.get('Descrição','')}</td>"
                     f"<td style='text-align:right'>{imp_str}</td></tr>")
        return f"""
  <div class="card">
    <h2>🔍 Log de Auditoria ({len(df)} problemas)</h2>
    <table><thead><tr>
      <th>Severidade</th><th>Tipo</th><th>Linha(s)</th>
      <th>Coluna</th><th>Descrição</th><th>Impacto R$</th>
    </tr></thead><tbody>{rows}</tbody></table>
  </div>
"""

    def _secao_aging(self, df: pd.DataFrame) -> str:
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
            rows += (f"<tr><td>{faixa}</td><td style='text-align:right'>{qtd}</td>"
                     f"<td style='text-align:right'>R$ {tot:,.2f}</td>"
                     f"<td style='text-align:right'>{pct:.1f}%</td>"
                     f"<td style='width:180px'>{bar}</td></tr>")
        return f"""
  <div class="card">
    <h2>📅 Aging de Recebíveis — Total: R$ {total:,.2f}</h2>
    <table><thead><tr>
      <th>Faixa</th><th style="text-align:right">Qtd</th>
      <th style="text-align:right">Valor</th>
      <th style="text-align:right">%</th><th>Distribuição</th>
    </tr></thead><tbody>{rows}</tbody></table>
  </div>
"""

    def _secao_dre(self, df: pd.DataFrame) -> str:
        rows = ''
        totais = {'(=) Receita Líquida', '(=) Lucro Bruto',
                  '(=) Resultado Operacional (EBIT)', '(=) Resultado antes IR/CSLL', '(=) Lucro Líquido'}
        for _, r in df.iterrows():
            linha = str(r.get('Linha_DRE', ''))
            valor = float(r.get('Valor_RS', 0))
            av    = f"{float(r['AV_%']):.1f}%" if 'AV_%' in r and pd.notna(r.get('AV_%')) else ''
            cls   = 'dre-total' if linha in totais else ('dre-sub' if linha.startswith('(-)') else '')
            cor   = '#C00000' if valor < 0 and linha in totais else ''
            rows += (f"<tr class='{cls}'><td>{linha}</td>"
                     f"<td style='text-align:right;color:{cor}'>R$ {valor:,.2f}</td>"
                     f"<td style='text-align:right;color:#888'>{av}</td></tr>")
        return f"""
  <div class="card">
    <h2>📊 DRE — Demonstrativo de Resultado</h2>
    <table><thead><tr><th>Linha</th><th style="text-align:right">Valor (R$)</th><th style="text-align:right">AV%</th></tr></thead>
    <tbody>{rows}</tbody></table>
  </div>
"""

    def _secao_pareto(self, df: pd.DataFrame) -> str:
        col_ent = df.columns[0]
        max_val = df['Total_RS'].max() if len(df) else 1
        rows = ''
        for _, r in df.head(15).iterrows():
            pct_bar = min(float(r.get('Total_RS', 0)) / max_val * 100, 100)
            classe  = str(r.get('Classe_Pareto', ''))
            cor_cls = '#1F4E79' if 'A' in classe else '#aaa'
            bar = f'<div class="bar-wrap"><div class="bar" style="width:{pct_bar:.1f}%;background:{cor_cls}"></div></div>'
            rows += (f"<tr><td style='text-align:center'>{int(r.get('Ranking',0))}</td>"
                     f"<td>{r[col_ent]}</td>"
                     f"<td style='text-align:right'>R$ {float(r.get('Total_RS',0)):,.2f}</td>"
                     f"<td style='text-align:right'>{float(r.get('Percentual',0)):.1f}%</td>"
                     f"<td style='text-align:right'>{float(r.get('Acumulado_%',0)):.1f}%</td>"
                     f"<td><span style='color:{cor_cls};font-weight:bold'>{classe}</span></td>"
                     f"<td style='width:120px'>{bar}</td></tr>")
        return f"""
  <div class="card">
    <h2>🏆 Análise Pareto — Top {min(15,len(df))} de {len(df)}</h2>
    <table><thead><tr>
      <th>#</th><th>{col_ent}</th>
      <th style="text-align:right">Total R$</th>
      <th style="text-align:right">%</th>
      <th style="text-align:right">Acumulado</th>
      <th>Classe</th><th>Participação</th>
    </tr></thead><tbody>{rows}</tbody></table>
  </div>
"""
