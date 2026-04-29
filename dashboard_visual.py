"""Gerador de dashboard HTML autônomo para apresentação executiva.

Gerado automaticamente por motor_automatico.py após processar cada arquivo.
Não requer servidor — abre diretamente no navegador.
"""
from __future__ import annotations

import html
import json
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


class GeradorDashboard:
    """Gera um dashboard HTML standalone com Chart.js."""

    @staticmethod
    def gerar(
        arquivo_origem: str,
        df_dados: pd.DataFrame,
        df_fluxo_mensal: pd.DataFrame | None = None,
        df_fluxo_diario: pd.DataFrame | None = None,
        df_fluxo_anual: pd.DataFrame | None = None,
        df_dre: pd.DataFrame | None = None,
        df_pareto: pd.DataFrame | None = None,
        total_criticos: int = 0,
        config: dict | None = None,
    ) -> str:
        """Retorna HTML completo do dashboard.

        Args:
            arquivo_origem: Nome do arquivo processado.
            df_dados: DataFrame no formato padrão do sistema.
            df_fluxo_mensal/diario/anual: Saída de AnalistaFinanceiro.resumo_periodo().
            df_dre: Demonstrativo de Resultado (opcional).
            df_pareto: Análise Pareto (opcional).
            total_criticos: Número de problemas críticos encontrados.
            config: Dict de configuração (para empresa/título/cores).
        """
        cfg = config or {}
        empresa = _esc(cfg.get('relatorio', {}).get('empresa', 'Empresa'))
        titulo  = _esc(cfg.get('relatorio', {}).get('titulo', 'Dashboard Financeiro'))
        agora   = datetime.now().strftime('%d/%m/%Y %H:%M')
        arquivo = _esc(Path(arquivo_origem).name)

        kpis = _calcular_kpis(df_dados, df_fluxo_mensal)
        chart_data = _montar_chart_data(df_fluxo_mensal)

        banner_cor  = '#D1FAE5' if total_criticos == 0 else '#FEE2E2'
        banner_txt  = '#065F46' if total_criticos == 0 else '#991B1B'
        banner_icon = '✓' if total_criticos == 0 else '⚠'
        banner_msg  = (
            'Análise concluída — dados prontos para apresentação.'
            if total_criticos == 0
            else f'{total_criticos} problema(s) crítico(s) detectado(s). Revise antes de apresentar.'
        )

        secao_fluxo  = _secao_fluxo_tabs(df_fluxo_diario, df_fluxo_mensal, df_fluxo_anual)
        secao_dre    = _secao_dre(df_dre)
        secao_pareto = _secao_pareto(df_pareto)

        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{titulo} — {empresa}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"
        crossorigin="anonymous"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',Arial,sans-serif;background:#F0F4F8;color:#1A2B3C;font-size:14px}}
.header{{background:linear-gradient(135deg,#1A3556,#0D1B2A);color:#fff;padding:28px 40px;display:flex;
  justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}}
.header h1{{font-size:22px;font-weight:700;letter-spacing:.5px}}
.header .meta{{font-size:12px;opacity:.75;margin-top:4px}}
.header .badge{{background:#C9A227;color:#000;padding:4px 12px;border-radius:20px;font-size:11px;font-weight:700}}
.banner{{margin:20px 40px 0;padding:12px 20px;border-radius:8px;font-weight:600;font-size:13px;
  background:{banner_cor};color:{banner_txt};border:1px solid {banner_txt}40}}
.main{{padding:20px 40px 40px}}
.kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px;margin-bottom:24px}}
.kpi{{background:#fff;border-radius:12px;padding:18px 20px;box-shadow:0 1px 4px #0001;
  border-top:4px solid #1A3556}}
.kpi.receita{{border-top-color:#065F46}}
.kpi.despesa{{border-top-color:#991B1B}}
.kpi.resultado{{border-top-color:#C9A227}}
.kpi .label{{font-size:11px;color:#6B7280;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}}
.kpi .valor{{font-size:22px;font-weight:700;line-height:1.1}}
.kpi .sub{{font-size:11px;color:#9BA8B5;margin-top:4px}}
.card{{background:#fff;border-radius:12px;padding:24px;box-shadow:0 1px 4px #0001;margin-bottom:20px}}
.card h2{{font-size:16px;font-weight:700;color:#1A3556;margin-bottom:16px;padding-bottom:8px;
  border-bottom:2px solid #E5E7EB}}
.chart-wrap{{position:relative;height:300px;margin-bottom:8px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{background:#1A3556;color:#fff;padding:8px 12px;text-align:left;font-weight:600;font-size:12px}}
td{{padding:7px 12px;border-bottom:1px solid #F3F4F6}}
tr:hover td{{background:#F9FAFB}}
.tabs{{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap}}
.tab-btn{{padding:6px 18px;border:1px solid #1A3556;border-radius:20px;cursor:pointer;
  background:#fff;color:#1A3556;font-size:13px;font-weight:600;transition:.15s}}
.tab-btn.active,.tab-btn:hover{{background:#1A3556;color:#fff}}
.footer{{text-align:center;font-size:11px;color:#9BA8B5;padding:20px;border-top:1px solid #E5E7EB}}
@media(max-width:600px){{.main,.banner,.header{{padding-left:16px;padding-right:16px}}}}
</style>
</head>
<body>
<header class="header">
  <div>
    <h1>{titulo}</h1>
    <div class="meta">{empresa} &bull; Arquivo: {arquivo} &bull; Gerado em {agora} UTC</div>
  </div>
  <div class="badge">Dashboard Autônomo</div>
</header>

<div class="banner">{banner_icon} {banner_msg}</div>

<main class="main">

<!-- KPIs -->
<div class="kpi-grid">
  <div class="kpi receita">
    <div class="label">Receitas</div>
    <div class="valor" style="color:#065F46">{_fmt_brl(kpis['receita_total'])}</div>
    <div class="sub">{kpis['nf_receita']} NFs vendidas</div>
  </div>
  <div class="kpi despesa">
    <div class="label">Despesas</div>
    <div class="valor" style="color:#991B1B">{_fmt_brl(kpis['despesa_total'])}</div>
    <div class="sub">{kpis['nf_despesa']} NFs recebidas</div>
  </div>
  <div class="kpi resultado">
    <div class="label">Resultado Líquido</div>
    <div class="valor" style="color:{'#065F46' if kpis['resultado']>=0 else '#991B1B'}">
      {_fmt_brl(kpis['resultado'])}</div>
    <div class="sub">Margem: {kpis['margem']:.1f}%</div>
  </div>
  <div class="kpi">
    <div class="label">Total de Registros</div>
    <div class="valor">{kpis['total_registros']}</div>
    <div class="sub">lançamentos processados</div>
  </div>
  <div class="kpi">
    <div class="label">Ticket Médio (Rec.)</div>
    <div class="valor">{_fmt_brl(kpis['ticket_medio'])}</div>
    <div class="sub">por NF de receita</div>
  </div>
  <div class="kpi">
    <div class="label">Alertas Críticos</div>
    <div class="valor" style="color:{'#991B1B' if total_criticos>0 else '#065F46'}">{total_criticos}</div>
    <div class="sub">{'revisar dados' if total_criticos>0 else 'dados íntegros'}</div>
  </div>
</div>

<!-- Gráfico Receita × Despesa -->
{_secao_grafico(chart_data)}

<!-- Fluxo por Período -->
{secao_fluxo}

<!-- DRE -->
{secao_dre}

<!-- Pareto -->
{secao_pareto}

</main>
<footer class="footer">
  Dashboard gerado automaticamente pelo Toolkit Financeiro &bull; {agora} UTC
</footer>

<script>
{_js_grafico(chart_data)}
{_js_tabs()}
</script>
</body></html>"""


# ── helpers privados ──────────────────────────────────────────────

def _esc(v) -> str:
    return html.escape(str(v) if v is not None else '')


def _fmt_brl(val, dec: int = 2) -> str:
    try:
        v = float(val)
        us = f"{abs(v):,.{dec}f}"
        br = us.replace(',', 'X').replace('.', ',').replace('X', '.')
        return f"R$ {'-' if v < 0 else ''}{br}"
    except (ValueError, TypeError):
        return '—'


def _calcular_kpis(df: pd.DataFrame, df_mensal: pd.DataFrame | None) -> dict:
    kpis = {
        'receita_total': 0.0, 'despesa_total': 0.0, 'resultado': 0.0,
        'margem': 0.0, 'nf_receita': 0, 'nf_despesa': 0,
        'total_registros': len(df) if df is not None else 0,
        'ticket_medio': 0.0,
    }
    if df_mensal is not None and len(df_mensal):
        kpis['receita_total'] = float(df_mensal['Receita_RS'].sum())
        kpis['despesa_total'] = float(df_mensal['Despesa_RS'].sum())
        kpis['resultado']     = float(df_mensal['Resultado_RS'].sum())
        kpis['nf_receita']    = int(df_mensal['NFs_Receita'].sum())
        kpis['nf_despesa']    = int(df_mensal['NFs_Despesa'].sum())
    elif df is not None and len(df) and 'Valor' in df.columns:
        valores = pd.to_numeric(df['Valor'], errors='coerce').fillna(0)
        if 'Tipo' in df.columns:
            tipos = df['Tipo'].astype(str).str.upper()
            kpis['receita_total'] = float(valores[tipos == 'RECEITA'].sum())
            kpis['despesa_total'] = float(valores[tipos == 'DESPESA'].sum())
            kpis['nf_receita']    = int((tipos == 'RECEITA').sum())
            kpis['nf_despesa']    = int((tipos == 'DESPESA').sum())
        else:
            kpis['receita_total'] = float(valores[valores >= 0].sum())
            kpis['despesa_total'] = float(valores[valores < 0].abs().sum())
        kpis['resultado'] = kpis['receita_total'] - kpis['despesa_total']

    if kpis['receita_total'] != 0:
        kpis['margem'] = kpis['resultado'] / kpis['receita_total'] * 100
        kpis['ticket_medio'] = (kpis['receita_total'] / kpis['nf_receita']
                                if kpis['nf_receita'] else 0)
    return kpis


def _montar_chart_data(df_mensal: pd.DataFrame | None) -> dict:
    if df_mensal is None or len(df_mensal) == 0:
        return {'labels': [], 'receitas': [], 'despesas': [], 'resultados': []}
    df = df_mensal.tail(24)  # últimos 24 períodos
    return {
        'labels':     [str(p) for p in df['Periodo']],
        'receitas':   [round(float(v), 2) for v in df['Receita_RS']],
        'despesas':   [round(float(v), 2) for v in df['Despesa_RS']],
        'resultados': [round(float(v), 2) for v in df['Resultado_RS']],
    }


def _secao_grafico(chart_data: dict) -> str:
    if not chart_data['labels']:
        return ''
    return """
<div class="card">
  <h2>📊 Receitas × Despesas por Período</h2>
  <div class="chart-wrap"><canvas id="chartFluxo" aria-label="Gráfico Receitas e Despesas"></canvas></div>
</div>"""


def _js_grafico(chart_data: dict) -> str:
    if not chart_data['labels']:
        return ''
    data_json = json.dumps(chart_data, ensure_ascii=False).replace('</', '<\\/')
    return f"""
(function(){{
  var d = {data_json};
  var ctx = document.getElementById('chartFluxo');
  if (!ctx) return;
  new Chart(ctx, {{
    type: 'bar',
    data: {{
      labels: d.labels,
      datasets: [
        {{label:'Receitas',data:d.receitas,backgroundColor:'rgba(6,95,70,.7)',borderRadius:4}},
        {{label:'Despesas',data:d.despesas,backgroundColor:'rgba(153,27,27,.7)',borderRadius:4}},
        {{label:'Resultado',data:d.resultados,type:'line',borderColor:'#C9A227',
          backgroundColor:'transparent',borderWidth:2,pointRadius:3,tension:.3}}
      ]
    }},
    options:{{
      responsive:true,maintainAspectRatio:false,
      plugins:{{legend:{{position:'top'}},tooltip:{{callbacks:{{
        label:function(c){{return c.dataset.label+': R$ '+c.parsed.y.toLocaleString('pt-BR',{{minimumFractionDigits:2}})}}
      }}}}}},
      scales:{{y:{{ticks:{{callback:function(v){{return 'R$ '+v.toLocaleString('pt-BR',{{minimumFractionDigits:2}})}}}}}}}}
    }}
  }});
}})();"""


def _tabela_fluxo(df: pd.DataFrame | None) -> str:
    if df is None or len(df) == 0:
        return '<p style="color:#6B7280;font-size:13px;padding:8px 0">Nenhum dado disponível.</p>'
    tot_rec  = float(df['Receita_RS'].sum())
    tot_desp = float(df['Despesa_RS'].sum())
    tot_res  = float(df['Resultado_RS'].sum())
    rows = ''
    for _, r in df.iterrows():
        res = float(r['Resultado_RS'])
        cor = '#D1FAE5' if res >= 0 else '#FEE2E2'
        pct = float(r['Resultado_Pct'])
        pct_str = (f'+{pct:.1f}%' if pct >= 0 else f'{pct:.1f}%')
        rows += (
            f"<tr style='background:{cor}'>"
            f"<td style='font-weight:600'>{_esc(str(r['Periodo']))}</td>"
            f"<td style='text-align:right;color:#065F46'>{_fmt_brl(r['Receita_RS'])}</td>"
            f"<td style='text-align:center'>{int(r['NFs_Receita'])}</td>"
            f"<td style='text-align:right;color:#991B1B'>{_fmt_brl(r['Despesa_RS'])}</td>"
            f"<td style='text-align:center'>{int(r['NFs_Despesa'])}</td>"
            f"<td style='text-align:right;font-weight:bold;color:{'#065F46' if res>=0 else '#991B1B'}'>"
            f"{_fmt_brl(res)}</td>"
            f"<td style='text-align:center'>{pct_str}</td></tr>"
        )
    cor_tot = '#D1FAE5' if tot_res >= 0 else '#FEE2E2'
    rows += (
        f"<tr style='background:{cor_tot};font-weight:bold;border-top:2px solid #1A3556'>"
        f"<td>TOTAL</td>"
        f"<td style='text-align:right;color:#065F46'>{_fmt_brl(tot_rec)}</td>"
        f"<td style='text-align:center'>—</td>"
        f"<td style='text-align:right;color:#991B1B'>{_fmt_brl(tot_desp)}</td>"
        f"<td style='text-align:center'>—</td>"
        f"<td style='text-align:right;color:{'#065F46' if tot_res>=0 else '#991B1B'}'>"
        f"{_fmt_brl(tot_res)}</td><td></td></tr>"
    )
    return f"""<div style="overflow-x:auto">
<table>
  <thead><tr>
    <th>Período</th>
    <th style="text-align:right">Receitas (R$)</th>
    <th style="text-align:center">NFs Vendidas</th>
    <th style="text-align:right">Despesas (R$)</th>
    <th style="text-align:center">NFs Recebidas</th>
    <th style="text-align:right">Resultado (R$)</th>
    <th style="text-align:center">Resultado %</th>
  </tr></thead><tbody>{rows}</tbody>
</table></div>"""


def _secao_fluxo_tabs(df_d, df_m, df_a) -> str:
    if not any(df is not None and len(df) > 0 for df in [df_d, df_m, df_a]):
        return ''
    tab_d = _tabela_fluxo(df_d)
    tab_m = _tabela_fluxo(df_m)
    tab_a = _tabela_fluxo(df_a)
    return f"""
<div class="card">
  <h2>📅 Fluxo por Período — Receitas × Despesas</h2>
  <div class="tabs">
    <button class="tab-btn active" onclick="showFluxo('m',this)">Mensal</button>
    <button class="tab-btn" onclick="showFluxo('d',this)">Diário</button>
    <button class="tab-btn" onclick="showFluxo('a',this)">Anual</button>
  </div>
  <div id="fluxo-d" style="display:none">{tab_d}</div>
  <div id="fluxo-m" style="display:block">{tab_m}</div>
  <div id="fluxo-a" style="display:none">{tab_a}</div>
</div>"""


_TOTAIS_DRE = {'(=) Receita Líquida', '(=) Lucro Bruto', '(=) Resultado Operacional (EBIT)',
               '(=) Resultado antes IR/CSLL', '(=) Lucro Líquido', '(=) EBIT (Resultado Operacional)'}


def _secao_dre(df: pd.DataFrame | None) -> str:
    if df is None or len(df) == 0:
        return ''
    rows = ''
    for _, r in df.iterrows():
        linha = _esc(str(r.get('Linha_DRE', r.iloc[0])))
        val   = float(r.get('Valor_RS', 0))
        av    = r.get('AV_%', '')
        nivel = str(r.get('Nivel', '')).strip()
        is_total = linha in _TOTAIS_DRE
        peso = 'font-weight:bold' if is_total else ''
        cor_v = '#065F46' if val >= 0 else '#991B1B'
        indent = 'padding-left:24px' if nivel == '2' else ''
        rows += (
            f"<tr><td style='{peso};{indent}'>{linha}</td>"
            f"<td style='text-align:right;{cor_v};{peso}'>{_fmt_brl(val)}</td>"
            f"<td style='text-align:center'>{_esc(str(av)) if av != '' else '—'}</td></tr>"
        )
    return f"""
<div class="card">
  <h2>📈 DRE — Demonstrativo de Resultado</h2>
  <div style="overflow-x:auto">
  <table>
    <thead><tr><th>Linha</th><th style="text-align:right">Valor R$</th>
    <th style="text-align:center">AV%</th></tr></thead>
    <tbody>{rows}</tbody>
  </table></div>
</div>"""


def _secao_pareto(df: pd.DataFrame | None) -> str:
    if df is None or len(df) == 0:
        return ''
    col_ent = df.columns[0]
    max_val = float(df['Total_RS'].max()) if len(df) else 1
    if not max_val or pd.isna(max_val):
        max_val = 1
    rows = ''
    for _, r in df.head(15).iterrows():
        nome    = _esc(str(r[col_ent]))
        val     = float(r.get('Total_RS', 0))
        pct     = float(r.get('Percentual', 0))
        acum    = float(r.get('Acumulado_%', 0))
        classe  = _esc(str(r.get('Classe_Pareto', '')))
        rank    = int(r.get('Ranking', 0))
        pct_bar = min(val / max_val * 100, 100)
        cor_cls = '#C9A227' if 'A' in classe else '#9BA8B5'
        rows += (
            f"<tr><td style='text-align:center'>{rank}</td>"
            f"<td>{nome}</td>"
            f"<td style='text-align:right;color:#065F46'>{_fmt_brl(val)}</td>"
            f"<td style='text-align:right'>{pct:.1f}%</td>"
            f"<td style='text-align:right'>{acum:.1f}%</td>"
            f"<td><span style='color:{cor_cls};font-weight:bold'>{classe}</span></td>"
            f"<td><div style='background:#E5E7EB;border-radius:4px;height:8px'>"
            f"<div style='background:{cor_cls};width:{pct_bar:.1f}%;height:8px;border-radius:4px'></div>"
            f"</div></td></tr>"
        )
    return f"""
<div class="card">
  <h2>🏆 Pareto — Top {min(15,len(df))} Entidades</h2>
  <div style="overflow-x:auto">
  <table>
    <thead><tr><th>#</th><th>{_esc(col_ent)}</th>
    <th style="text-align:right">Total R$</th>
    <th style="text-align:right">%</th>
    <th style="text-align:right">Acumulado</th>
    <th>Classe</th><th>Participação</th></tr></thead>
    <tbody>{rows}</tbody>
  </table></div>
</div>"""


def _js_tabs() -> str:
    return """
function showFluxo(id, btn) {
  ['d','m','a'].forEach(function(t) {
    var el = document.getElementById('fluxo-'+t);
    if (el) el.style.display = (t === id) ? 'block' : 'none';
  });
  document.querySelectorAll('.tab-btn').forEach(function(b) {
    b.classList.remove('active');
  });
  if (btn) btn.classList.add('active');
}"""
