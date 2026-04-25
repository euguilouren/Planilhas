"""
COMO USAR
=========
1. Coloque sua planilha na mesma pasta deste arquivo
2. Edite a seção "CONFIGURAÇÃO" abaixo
3. Execute:  python rodar.py
4. Abra o arquivo resultado.xlsx gerado
5. Copie o conteúdo de briefing.txt e cole no Claude para análise
"""

import logging
import os
from datetime import datetime
from pathlib import Path

import pandas as pd

try:
    import yaml as _yaml
    _YAML_OK = True
except ImportError:
    _YAML_OK = False

from toolkit_financeiro import (
    Leitor, Auditor, Conciliador, AnalistaFinanceiro,
    AnalistaComercial, MontadorPlanilha, Verificador,
    PipelineFinanceiro, Util, PrestadorContas, Status
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S',
)
logger = logging.getLogger(__name__)

# ── Carregar config.yaml se disponível ──────────────────────────
def _carregar_config() -> dict:
    cfg_path = Path(__file__).with_name('config.yaml')
    if _YAML_OK and cfg_path.exists():
        try:
            with open(cfg_path, encoding='utf-8') as f:
                cfg = _yaml.safe_load(f) or {}
            logger.info("Configuração carregada de config.yaml")
            return cfg
        except Exception as e:
            logger.warning("Não foi possível ler config.yaml: %s — usando defaults", e)
    return {}

_CFG = _carregar_config()
_COLS_CFG = _CFG.get('colunas', {})
_AUD_CFG  = _CFG.get('auditoria', {})

# ══════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO — edite aqui (ou deixe config.yaml controlar)
# ══════════════════════════════════════════════════════════════════

ARQUIVO_ENTRADA  = "minha_planilha.xlsx"   # nome do seu arquivo
ARQUIVO_SAIDA    = "resultado.xlsx"        # nome do arquivo de saída
ARQUIVO_BRIEFING = "briefing.txt"          # resumo para colar no Claude

# Nomes das colunas — lidos do config.yaml; edite aqui para sobrescrever
COL_VALOR    = _COLS_CFG.get('valor',     'Valor')
COL_CATEGORIA= _COLS_CFG.get('categoria', 'Categoria')
COL_DATA     = _COLS_CFG.get('data',      'Data')
COL_CHAVE    = _COLS_CFG.get('chave',     'NF')
COL_ENTIDADE = _COLS_CFG.get('entidade',  'Cliente')

# Colunas obrigatórias para checar se estão vazias
COLUNAS_OBRIGATORIAS = [c for c in _CFG.get('colunas_obrigatorias', [COL_VALOR, COL_DATA, COL_CHAVE])]

# ══════════════════════════════════════════════════════════════════
# EXECUÇÃO — não precisa editar abaixo
# ══════════════════════════════════════════════════════════════════

def main() -> None:
    print(f"\n{'='*55}")
    print("  TOOLKIT FINANCEIRO — iniciando processamento")
    print("  Powered by Luan Guilherme Lourenço")
    print(f"{'='*55}")
    logger.info("Arquivo de entrada: %s", ARQUIVO_ENTRADA)
    logger.info("Arquivo de saída:   %s", ARQUIVO_SAIDA)
    print()

    # ── 1. Verificar se o arquivo existe ────────────────────────
    if not os.path.exists(ARQUIVO_ENTRADA):
        print(f"[ERRO] Arquivo '{ARQUIVO_ENTRADA}' não encontrado.")
        print("       Coloque o arquivo na mesma pasta que este script.")
        return

    # ── 2. Ler e diagnosticar ────────────────────────────────────
    print("[1/5] Lendo arquivo e gerando diagnóstico...")
    resultado = Leitor.ler_arquivo(ARQUIVO_ENTRADA)
    dados       = resultado['dados']
    diagnostico = resultado['diagnostico']
    print(Leitor.resumo_diagnostico(diagnostico))

    # Pegar a primeira aba como principal
    nome_aba = list(dados.keys())[0]
    df = dados[nome_aba]
    print(f"\n      Aba utilizada: '{nome_aba}' ({len(df):,} registros)\n")

    # ── 3. Auditoria ─────────────────────────────────────────────
    print("[2/5] Executando auditoria...")
    inconsistencias = []

    if COL_CHAVE in df.columns:
        dups = Auditor.detectar_duplicatas(df, [COL_CHAVE], nome_aba)
        if len(dups):
            print(f"      [ALERTA] {len(dups)} possíveis duplicatas encontradas")
            for _, row in dups.iterrows():
                inconsistencias.append({
                    'aba': nome_aba, 'linha': int(row.get('_linha_excel', 0)),
                    'coluna': COL_CHAVE, 'tipo': 'DUPLICATA',
                    'severidade': Status.CRITICA,
                    'valor': str(row.get(COL_CHAVE, '')),
                    'descricao': f"Duplicata em '{COL_CHAVE}'",
                    'impacto_rs': 0,
                })

    if COL_VALOR in df.columns:
        outliers = Auditor.detectar_outliers(df, COL_VALOR, aba=nome_aba)
        if len(outliers):
            print(f"      [ALERTA] {len(outliers)} outliers detectados em '{COL_VALOR}'")
            for _, row in outliers.iterrows():
                inconsistencias.append({
                    'aba': nome_aba, 'linha': int(row.get('_linha_excel', 0)),
                    'coluna': COL_VALOR, 'tipo': 'OUTLIER',
                    'severidade': Status.MEDIA,
                    'valor': str(row.get(COL_VALOR, '')),
                    'descricao': f"Valor fora do padrão (±{row.get('_desvio_padrao','')})",
                    'impacto_rs': 0,
                })

    if COL_DATA in df.columns:
        temp = Auditor.detectar_inconsistencias_temporais(df, COL_DATA, aba=nome_aba)
        inconsistencias.extend(temp)
        if temp:
            print(f"      [ALERTA] {len(temp)} inconsistências de data encontradas")

    inconsistencias.extend(
        Auditor.detectar_campos_vazios(df, COLUNAS_OBRIGATORIAS, nome_aba)
    )

    df_auditoria = Auditor.relatorio_auditoria(inconsistencias)
    criticos = len(df_auditoria[df_auditoria['Severidade'] == Status.CRITICA]) if len(df_auditoria) else 0
    print(f"      Total de problemas: {len(inconsistencias)} ({criticos} críticos)\n")

    # ── 4. Análises ──────────────────────────────────────────────
    print("[3/5] Gerando análises financeiras e comerciais...")

    # Aging (se tiver coluna de data e valor)
    df_aging = None
    if COL_DATA in df.columns and COL_VALOR in df.columns:
        try:
            df_aging = AnalistaFinanceiro.calcular_aging(df, COL_DATA, COL_VALOR)
            print("      Aging calculado")
        except (KeyError, ValueError, TypeError) as e:
            logger.warning("Aging ignorado: %s", e)

    # DRE (se tiver categoria e valor)
    df_dre = None
    if COL_CATEGORIA in df.columns and COL_VALOR in df.columns:
        try:
            df_dre = AnalistaFinanceiro.construir_dre(df, COL_CATEGORIA, COL_VALOR)
            print("      DRE construído")
        except (KeyError, ValueError, AttributeError) as e:
            logger.warning("DRE ignorado: %s", e)

    # Pareto (se tiver entidade e valor)
    df_pareto = None
    if COL_ENTIDADE in df.columns and COL_VALOR in df.columns:
        try:
            df_pareto = AnalistaComercial.pareto(df, COL_ENTIDADE, COL_VALOR)
            print("      Análise Pareto concluída")
        except (KeyError, ValueError, ZeroDivisionError) as e:
            logger.warning("Pareto ignorado: %s", e)

    # Ticket médio
    df_ticket = None
    if COL_VALOR in df.columns:
        try:
            col_grupo = COL_ENTIDADE if COL_ENTIDADE in df.columns else None
            df_ticket = AnalistaComercial.ticket_medio(df, COL_VALOR, col_grupo)
            print("      Ticket médio calculado")
        except (KeyError, ValueError, TypeError) as e:
            logger.warning("Ticket médio ignorado: %s", e)

    print()

    # ── 5. Montar planilha ───────────────────────────────────────
    print("[4/5] Montando planilha Excel de resultado...")
    montador = MontadorPlanilha()

    # Aba de dados brutos
    montador.adicionar_aba(
        "Dados", df,
        titulo=f"DADOS — {nome_aba}",
        cols_moeda=[COL_VALOR] if COL_VALOR in df.columns else [],
        cols_data=[COL_DATA]   if COL_DATA  in df.columns else [],
        cols_soma=[COL_VALOR]  if COL_VALOR in df.columns else [],
    )

    # Aba de auditoria
    if len(df_auditoria):
        montador.adicionar_aba(
            "Auditoria", df_auditoria,
            titulo="LOG DE AUDITORIA",
            col_status="Severidade",
            cols_moeda=["Impacto R$"] if "Impacto R$" in df_auditoria.columns else [],
        )

    # Aba de aging
    if df_aging is not None and len(df_aging):
        montador.adicionar_aba(
            "Aging", df_aging,
            titulo="ANÁLISE DE AGING",
            cols_moeda=["Total_RS"],
        )

    # Aba de DRE
    if df_dre is not None and len(df_dre):
        montador.adicionar_aba(
            "DRE", df_dre,
            titulo="DEMONSTRATIVO DE RESULTADO",
            cols_moeda=["Valor_RS"],
            adicionar_totais=False,
        )

    # Aba de Pareto
    if df_pareto is not None and len(df_pareto):
        montador.adicionar_aba(
            "Pareto", df_pareto,
            titulo="ANÁLISE PARETO",
            cols_moeda=["Total_RS"],
        )

    # Resumo executivo com métricas-chave
    metricas = {}
    if COL_VALOR in df.columns:
        total = pd.to_numeric(df[COL_VALOR], errors='coerce').sum()
        media = pd.to_numeric(df[COL_VALOR], errors='coerce').mean()
        metricas["Total Geral"] = {'valor': total, 'tipo': 'moeda', 'status': Status.OK}
        metricas["Ticket Médio"] = {'valor': media, 'tipo': 'moeda', 'status': Status.OK}
    metricas["Total de Registros"] = {'valor': len(df), 'tipo': 'numero', 'status': Status.OK}
    metricas["Problemas Críticos"] = {
        'valor': criticos, 'tipo': 'numero',
        'status': Status.OK if criticos == 0 else Status.DIVERGENTE,
        'obs': f"{len(inconsistencias)} total de alertas",
    }
    montador.adicionar_resumo_executivo(metricas)
    montador.salvar(ARQUIVO_SAIDA)
    print(f"      Planilha salva: {ARQUIVO_SAIDA}\n")

    # ── 6. Gerar briefing para o Claude ─────────────────────────
    print("[5/5] Gerando briefing para o Claude...")
    briefing = _gerar_briefing(
        df, diagnostico, df_auditoria, df_dre,
        df_aging, df_pareto, df_ticket, inconsistencias
    )
    with open(ARQUIVO_BRIEFING, 'w', encoding='utf-8') as f:
        f.write(briefing)
    print(f"      Briefing salvo: {ARQUIVO_BRIEFING}")
    print(f"\n{'='*55}")
    print("  CONCLUÍDO")
    print(f"  Abra '{ARQUIVO_SAIDA}' para ver a planilha formatada.")
    print(f"  Copie '{ARQUIVO_BRIEFING}' e cole no Claude para análise.")
    print(f"{'='*55}\n")


def _gerar_briefing(df, diagnostico, df_auditoria, df_dre,
                    df_aging, df_pareto, df_ticket, inconsistencias) -> str:
    """Gera texto compacto com os achados principais — para colar no Claude."""
    linhas = [
        f"# BRIEFING FINANCEIRO — {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        f"Arquivo: {diagnostico['arquivo']}",
        f"Total de registros: {diagnostico['total_registros']:,}",
        "",
    ]

    # Diagnóstico de formato
    if diagnostico['problemas_formato']:
        linhas.append(f"## Problemas de formato ({len(diagnostico['problemas_formato'])})")
        for p in diagnostico['problemas_formato']:
            linhas.append(f"- [{p['severidade']}] {p['descricao']}")
        linhas.append("")

    # Auditoria
    if len(df_auditoria):
        linhas.append(f"## Auditoria — {len(df_auditoria)} problemas encontrados")
        for sev in [Status.CRITICA, Status.ALTA, Status.MEDIA, Status.BAIXA]:
            subset = df_auditoria[df_auditoria['Severidade'] == sev]
            if len(subset):
                linhas.append(f"\n### {sev} ({len(subset)})")
                for _, row in subset.head(10).iterrows():
                    linhas.append(f"- Linha {row.get('Linha','?')} | {row.get('Coluna','?')} | {row.get('Descrição','')}")
        linhas.append("")

    # DRE resumido
    if df_dre is not None and len(df_dre):
        linhas.append("## DRE Resumido")
        for _, row in df_dre.iterrows():
            av = f" ({row['AV_%']:.1f}%)" if 'AV_%' in row and pd.notna(row.get('AV_%')) else ""
            linhas.append(f"  {row['Linha_DRE']:<40} R$ {row['Valor_RS']:>15,.2f}{av}")
        linhas.append("")

    # Aging
    if df_aging is not None and len(df_aging):
        linhas.append("## Aging de Recebíveis")
        for _, row in df_aging.iterrows():
            linhas.append(f"  {row['Faixa_Aging']:<25} {row['Quantidade']:>5} itens  R$ {row['Total_RS']:>12,.2f}  ({row.get('Percentual',0):.1f}%)")
        linhas.append("")

    # Pareto top 5
    if df_pareto is not None and len(df_pareto):
        linhas.append("## Top 5 por Faturamento (Pareto)")
        for _, row in df_pareto.head(5).iterrows():
            col_entidade = df_pareto.columns[0]
            linhas.append(f"  #{int(row['Ranking'])} {str(row[col_entidade]):<30} R$ {row['Total_RS']:>12,.2f}  ({row['Percentual']:.1f}%)")
        linhas.append("")

    # Ticket médio
    if df_ticket is not None and len(df_ticket):
        linhas.append("## Ticket Médio")
        if 'Ticket_Medio_RS' in df_ticket.columns:
            for _, row in df_ticket.head(5).iterrows():
                linhas.append(f"  Ticket médio: R$ {row['Ticket_Medio_RS']:,.2f} | {int(row.get('Transações',0))} transações")
        linhas.append("")

    linhas += [
        "---",
        "Arquivo Excel completo gerado localmente.",
        "Analise os dados acima e me indique:",
        "1. Quais inconsistências são mais críticas?",
        "2. O que o DRE indica sobre a saúde financeira?",
        "3. Quais ações recomenda com base no aging?",
    ]
    return '\n'.join(linhas)


if __name__ == "__main__":
    main()
