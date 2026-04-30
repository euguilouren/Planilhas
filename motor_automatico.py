"""
MOTOR AUTÔNOMO — Toolkit Financeiro
====================================
Monitora pasta_entrada/ e processa automaticamente qualquer
planilha Excel ou CSV que for colocada lá.

Execução:
    python motor_automatico.py            # roda continuamente
    python motor_automatico.py --once     # processa uma vez e sai
    python motor_automatico.py --arquivo minha.xlsx  # processa arquivo específico
"""

import os
import ssl
import html as _html_mod
import time
import logging
import smtplib
import argparse
import traceback
from email.mime.text        import MIMEText
from email.mime.multipart   import MIMEMultipart
from datetime               import datetime, timezone
from pathlib                import Path

import yaml
import pandas as pd

from toolkit_financeiro import (
    Leitor, Auditor, AnalistaFinanceiro, AnalistaComercial,
    MontadorPlanilha, Status, validar_config,
    Normalizador,
)
from relatorio_html import GeradorHTML
from dashboard_visual import GeradorDashboard

# ── Logging ───────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S',
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════
# CARREGAMENTO DE CONFIGURAÇÃO
# ══════════════════════════════════════════════════════════════════


def carregar_config(caminho: str = 'config.yaml') -> dict:
    if not os.path.exists(caminho):
        logger.warning("config.yaml não encontrado — usando configuração padrão")
        return {}
    try:
        with open(caminho, encoding='utf-8') as f:
            cfg = yaml.safe_load(f) or {}
    except yaml.YAMLError as exc:
        raise SystemExit(f"config.yaml malformado: {exc}") from exc
    avisos = validar_config(cfg)
    for aviso in avisos:
        logger.warning("config.yaml: %s", aviso)
    if cfg.get('validacao', {}).get('falhar_em_config_invalida', False) and avisos:
        raise SystemExit(f"Configuração inválida ({len(avisos)} erros). Corrija config.yaml.")
    return cfg


# ══════════════════════════════════════════════════════════════════
# INTEGRAÇÃO CLAUDE API
# ══════════════════════════════════════════════════════════════════

class AnalisadorClaudeAPI:
    """Envia briefing ao Claude API e retorna análise textual."""

    def __init__(self, cfg: dict):
        self.cfg_api = cfg.get('claude_api', {})
        self.ativo   = self.cfg_api.get('ativo', False)
        self.modelo  = self.cfg_api.get('modelo', 'claude-opus-4-5')
        self.max_tok = self.cfg_api.get('max_tokens', 1024)
        self._client = None
        self._system_prompt = ''

        if not self.ativo:
            return

        api_key = os.environ.get('ANTHROPIC_API_KEY', '')
        if not api_key:
            logger.warning(
                "claude_api.ativo=true mas ANTHROPIC_API_KEY não definida"
                " — análise Claude desabilitada."
            )
            self.ativo = False
            return

        try:
            import anthropic as _anthropic
            self._client = _anthropic.Anthropic(api_key=api_key)
        except ImportError:
            logger.warning(
                "Pacote 'anthropic' não instalado (pip install anthropic)"
                " — análise Claude desabilitada."
            )
            self.ativo = False
            return

        prompt_path = self.cfg_api.get('prompt_sistema', 'prompt_sistema.md')
        try:
            with open(prompt_path, encoding='utf-8') as f:
                self._system_prompt = f.read()
        except OSError as e:
            logger.warning("Não foi possível ler '%s': %s — usando prompt padrão.", prompt_path, e)
            self._system_prompt = (
                "Você é um analista financeiro sênior. Analise o briefing e indique "
                "os pontos críticos, diagnóstico e ações recomendadas."
            )

    def analisar(self, briefing: str) -> str:
        """Envia briefing ao Claude e retorna análise. Retorna '' se inativo ou erro."""
        if not self.ativo or self._client is None:
            return ''

        import anthropic as _anthropic
        try:
            resposta = self._client.messages.create(
                model=self.modelo,
                max_tokens=self.max_tok,
                system=[{
                    "type": "text",
                    "text": self._system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=[{"role": "user", "content": briefing}],
            )
            if not resposta.content:
                return ''
            for bloco in resposta.content:
                if getattr(bloco, 'type', None) == 'text':
                    return bloco.text
            return ''
        except _anthropic.AuthenticationError as e:
            logger.error("Claude API: chave inválida — %s", e)
        except _anthropic.RateLimitError as e:
            logger.warning("Claude API: rate limit atingido — %s", e)
        except _anthropic.APIConnectionError as e:
            logger.warning("Claude API: falha de conexão — %s", e)
        except _anthropic.APIError as e:
            logger.warning("Claude API: erro inesperado — %s", e)
        return ''


# ══════════════════════════════════════════════════════════════════
# PROCESSADOR PRINCIPAL
# ══════════════════════════════════════════════════════════════════

class ProcessadorArquivo:
    """Processa um arquivo financeiro e gera relatório HTML + Excel."""

    EXTENSOES_SUPORTADAS = {'.xlsx', '.xls', '.xlsm', '.csv', '.tsv', '.ofx'}

    def __init__(self, config: dict):
        self.cfg      = config
        self.cols     = config.get('colunas', {})
        self.gerador  = GeradorHTML(config)
        self.pasta_saida = Path(config.get('pastas', {}).get('saida', 'pasta_saida'))
        self.pasta_saida.mkdir(parents=True, exist_ok=True)
        self.analisador_claude = AnalisadorClaudeAPI(config)

        # Configurar logging para arquivo (guardamos referência para fechar depois)
        log_path = config.get('pastas', {}).get('log', str(self.pasta_saida / 'log.txt'))
        # Evitar handlers duplicados se múltiplas instâncias forem criadas
        if not any(isinstance(h, logging.FileHandler) and h.baseFilename == str(Path(log_path).resolve())
                   for h in logger.handlers):
            fh = logging.FileHandler(log_path, encoding='utf-8')
            fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
            logger.addHandler(fh)
            self._log_handler: logging.FileHandler = fh
        else:
            self._log_handler = None

    def __del__(self):
        if getattr(self, '_log_handler', None):
            try:
                logger.removeHandler(self._log_handler)
                self._log_handler.close()
            except Exception:
                pass

    MAX_TAMANHO_BYTES = 100 * 1024 * 1024  # 100 MB

    @staticmethod
    def _validar_caminho_arquivo(caminho: str, max_bytes: int = None) -> Path:
        """Resolve o caminho, bloqueia symlinks e valida tamanho máximo."""
        try:
            p = Path(caminho).resolve()
        except (OSError, ValueError) as exc:
            raise ValueError(f"Caminho inválido: {caminho}") from exc
        if p.suffix.lower() not in ProcessadorArquivo.EXTENSOES_SUPORTADAS:
            raise ValueError(f"Extensão '{p.suffix}' não suportada.")
        limite = max_bytes or ProcessadorArquivo.MAX_TAMANHO_BYTES
        try:
            tamanho = p.stat().st_size
            if tamanho > limite:
                mb = tamanho // (1024 * 1024)
                raise ValueError(f"Arquivo muito grande ({mb} MB). Máximo permitido: {limite // (1024*1024)} MB.")
        except OSError:
            pass  # arquivo ainda não existe ou sem permissão de stat — será tratado em processar()
        return p

    def processar(self, caminho_arquivo: str) -> dict:
        """
        Pipeline completo: lê → audita → analisa → gera HTML + Excel.
        Retorna dict com caminhos dos arquivos gerados e resumo.
        """
        caminho_arquivo = str(self._validar_caminho_arquivo(caminho_arquivo))
        nome_base = Path(caminho_arquivo).stem
        timestamp = datetime.now(tz=timezone.utc).strftime('%Y%m%d_%H%M%S')
        prefixo   = f"{nome_base}_{timestamp}"

        logger.info("=" * 55)
        logger.info("Processando: %s", caminho_arquivo)

        resultado = {
            'arquivo_origem':  caminho_arquivo,
            'timestamp':       timestamp,
            'html':            None,
            'xlsx':            None,
            'analise':         None,
            'criticos':        0,
            'total_problemas': 0,
            'status':          'OK',
            'erro':            None,
        }

        try:
            # ── 1. Leitura ──────────────────────────────────────
            logger.info("[1/5] Lendo arquivo...")
            leitura     = Leitor.ler_arquivo(caminho_arquivo)
            dados       = leitura['dados']
            diagnostico = leitura['diagnostico']
            if not dados:
                raise ValueError("Nenhuma aba encontrada no arquivo.")
            nome_aba    = list(dados.keys())[0]
            df          = dados[nome_aba].copy()
            logger.info("      %d registros | %d colunas", len(df), len(df.columns))

            # Auto-detectar e normalizar ERP
            df = self._normalizar_colunas(df)

            # Colunas configuradas
            col_val  = self.cols.get('valor',      'Valor')
            col_cat  = self.cols.get('categoria',  'Categoria')
            col_data = self.cols.get('data',       'Data')
            col_venc = self.cols.get('vencimento', 'Vencimento')
            col_chav = self.cols.get('chave',      'NF')
            col_ent  = self.cols.get('entidade',   'Cliente')
            col_obrig = self.cfg.get('colunas_obrigatorias', [col_val, col_data])

            # ── 1b. Conversão para planilha padrão ───────────────
            logger.info("[1b] Convertendo para formato padrão do sistema...")
            mapeamento_padrao = {
                'NF':         col_chav,
                'Data':       col_data,
                'Vencimento': col_venc,
                'Valor':      col_val,
                'Categoria':  col_cat,
                'Cliente':    col_ent,
            }
            df_padrao = Normalizador.para_padrao(df, mapeamento_padrao)

            # Validar formato padrão antes de continuar
            problemas_padrao = Normalizador.validar(df_padrao)
            criticos_padrao  = [p for p in problemas_padrao if p['severidade'] == Status.CRITICA]
            if criticos_padrao:
                logger.warning("      %d problema(s) crítico(s) no formato padrão:", len(criticos_padrao))
                for p in criticos_padrao:
                    logger.warning("      [%s] %s: %s", p['severidade'], p['tipo'], p['descricao'])

            # Salvar planilha padronizada
            caminho_padrao = self.pasta_saida / f"padrao_{prefixo}.xlsx"
            df_padrao.to_excel(str(caminho_padrao), index=False)
            resultado['padrao'] = str(caminho_padrao)
            logger.info("      Planilha padrão: %s", caminho_padrao.name)

            # A partir daqui trabalha com o DataFrame padronizado
            df      = df_padrao
            col_val  = 'Valor'
            col_cat  = 'Categoria'
            col_data = 'Data'
            col_venc = 'Vencimento'
            col_chav = 'NF'
            col_ent  = 'Cliente'
            col_obrig = ['NF', 'Data', 'Valor']

            # ── 2. Auditoria ─────────────────────────────────────
            logger.info("[2/5] Auditoria...")
            inconsistencias = []

            if col_chav in df.columns:
                self._coletar_dups(df, col_chav, nome_aba, inconsistencias)

            if col_val in df.columns:
                self._coletar_outliers(df, col_val, nome_aba, inconsistencias)

            if col_data in df.columns:
                inc = Auditor.detectar_inconsistencias_temporais(df, col_data, aba=nome_aba)
                inconsistencias.extend(inc)

            inconsistencias.extend(
                Auditor.detectar_campos_vazios(df, col_obrig, nome_aba)
            )

            df_auditoria  = Auditor.relatorio_auditoria(inconsistencias)
            total_criticos = len(df_auditoria[df_auditoria['Severidade'] == str(Status.CRITICA)]) if len(df_auditoria) else 0
            resultado['criticos']        = total_criticos
            resultado['total_problemas'] = len(df_auditoria)
            logger.info("      %d problemas (%d críticos)", len(df_auditoria), total_criticos)

            # ── 3. Análises ──────────────────────────────────────
            logger.info("[3/5] Análises financeiras...")
            df_aging  = self._calcular_aging(df, col_venc, col_val)
            df_dre    = self._construir_dre(df, col_cat, col_val)
            df_pareto = self._calcular_pareto(df, col_ent, col_val)
            df_ticket = self._calcular_ticket(df, col_val, col_ent)

            # Resumos por período (diário/mensal/anual)
            df_fluxo_d = AnalistaFinanceiro.resumo_periodo(df, freq='D')
            df_fluxo_m = AnalistaFinanceiro.resumo_periodo(df, freq='M')
            df_fluxo_a = AnalistaFinanceiro.resumo_periodo(df, freq='A')
            logger.info("      Fluxo: %d dias | %d meses | %d anos",
                        len(df_fluxo_d), len(df_fluxo_m), len(df_fluxo_a))

            # ── 4. Relatório HTML ─────────────────────────────────
            logger.info("[4/5] Gerando HTML...")
            html = self.gerador.gerar(
                arquivo_origem=Path(caminho_arquivo).name,
                df_dados=df,
                df_auditoria=df_auditoria,
                df_aging=df_aging,
                df_dre=df_dre,
                df_pareto=df_pareto,
                df_ticket=df_ticket,
                diagnostico=diagnostico,
                df_fluxo_diario=df_fluxo_d,
                df_fluxo_mensal=df_fluxo_m,
                df_fluxo_anual=df_fluxo_a,
            )
            caminho_html = self.pasta_saida / f"relatorio_{prefixo}.html"
            caminho_html.write_text(html, encoding='utf-8')
            resultado['html'] = str(caminho_html)
            logger.info("      HTML: %s", caminho_html)

            # Dashboard autônomo
            dash_html = GeradorDashboard.gerar(
                arquivo_origem=Path(caminho_arquivo).name,
                df_dados=df,
                df_fluxo_mensal=df_fluxo_m,
                df_fluxo_diario=df_fluxo_d,
                df_fluxo_anual=df_fluxo_a,
                df_dre=df_dre,
                df_pareto=df_pareto,
                total_criticos=total_criticos,
                config=self.cfg,
            )
            caminho_dash = self.pasta_saida / f"dashboard_{prefixo}.html"
            caminho_dash.write_text(dash_html, encoding='utf-8')
            resultado['dashboard'] = str(caminho_dash)
            logger.info("      Dashboard: %s", caminho_dash.name)

            # ── 5. Excel formatado ────────────────────────────────
            logger.info("[5/5] Gerando Excel...")
            caminho_xlsx = self.pasta_saida / f"resultado_{prefixo}.xlsx"
            montador = MontadorPlanilha()

            montador.adicionar_aba('Dados', df, titulo=f'DADOS — {nome_aba}',
                cols_moeda=[col_val] if col_val in df.columns else [],
                cols_data=[col_data] if col_data in df.columns else [],
                cols_soma=[col_val]  if col_val in df.columns else [])

            if len(df_auditoria):
                montador.adicionar_aba('Auditoria', df_auditoria,
                    titulo='LOG DE AUDITORIA', col_status='Severidade',
                    cols_moeda=['Impacto R$'] if 'Impacto R$' in df_auditoria.columns else [])

            if df_aging is not None and len(df_aging):
                montador.adicionar_aba('Aging', df_aging, titulo='AGING',
                    cols_moeda=['Total_RS'], adicionar_totais=False)

            if df_dre is not None and len(df_dre):
                montador.adicionar_aba('DRE', df_dre, titulo='DRE',
                    cols_moeda=['Valor_RS'], adicionar_totais=False)

            if df_pareto is not None and len(df_pareto):
                montador.adicionar_aba('Pareto', df_pareto, titulo='PARETO',
                    cols_moeda=['Total_RS'])

            metricas = self._montar_metricas(df, df_auditoria, col_val, total_criticos)
            montador.adicionar_resumo_executivo(metricas)
            montador.salvar(str(caminho_xlsx))
            resultado['xlsx'] = str(caminho_xlsx)
            logger.info("      Excel: %s", caminho_xlsx)

            # ── Relatório de ações corretivas ─────────────────────
            if total_criticos > 0 or len(df_auditoria) > 0:
                resultado['status'] = 'ALERTA' if total_criticos > 0 else 'AVISO'
                caminho_acoes = self.pasta_saida / f"acoes_{prefixo}.html"
                html_acoes = self._gerar_relatorio_acoes(resultado, df_auditoria)
                caminho_acoes.write_text(html_acoes, encoding='utf-8')
                resultado['acoes'] = str(caminho_acoes)
                logger.info("      Ações: %s", caminho_acoes.name)

            # ── 6. Análise Claude API ─────────────────────────────
            if self.analisador_claude.ativo:
                logger.info("[6/6] Enviando briefing ao Claude API...")
                briefing = self._gerar_briefing(
                    df, diagnostico, df_auditoria, df_dre,
                    df_aging, df_pareto, df_ticket, df_fluxo_m
                )
                analise = self.analisador_claude.analisar(briefing)
                if analise:
                    caminho_analise = self.pasta_saida / f"analise_{prefixo}.txt"
                    caminho_analise.write_text(analise, encoding='utf-8')
                    resultado['analise'] = str(caminho_analise)
                    logger.info("      Análise Claude: %s", caminho_analise)

            # ── Alerta por e-mail ─────────────────────────────────
            if total_criticos > 0:
                self._enviar_email(resultado, df_auditoria)

            logger.info("CONCLUÍDO — criticos=%d | html=%s",
                        total_criticos, caminho_html.name)

        except (FileNotFoundError, PermissionError) as exc:
            resultado['status'] = 'ERRO'
            resultado['erro']   = str(exc)
            logger.error("Arquivo inacessível %s: %s", caminho_arquivo, exc)
        except (pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
            resultado['status'] = 'ERRO'
            resultado['erro']   = str(exc)
            logger.error("Dados inválidos em %s: %s", caminho_arquivo, exc)
        except (ValueError, KeyError) as exc:
            resultado['status'] = 'ERRO'
            resultado['erro']   = str(exc)
            logger.error("Erro de dados em %s: %s", caminho_arquivo, exc)
        except RuntimeError as exc:
            resultado['status'] = 'ERRO'
            resultado['erro']   = str(exc)
            logger.error("Erro de processamento em %s: %s", caminho_arquivo, exc)
        except Exception as exc:
            resultado['status'] = 'ERRO'
            resultado['erro']   = str(exc)
            logger.error("Erro inesperado em %s: %s", caminho_arquivo, exc)
            logger.debug(traceback.format_exc())

        return resultado

    # ── Helpers internos ──────────────────────────────────────────

    def _normalizar_colunas(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detecta ERP de origem e normaliza colunas usando base_conhecimento (20 ERPs)."""
        from base_conhecimento import detectar_erp, normalizar_colunas
        erp = detectar_erp(df)
        if erp:
            logger.info("      ERP detectado: %s", erp)
            return normalizar_colunas(df, erp)
        return df

    def _coletar_dups(self, df, col_chav, aba, lista):
        for _, row in Auditor.detectar_duplicatas(df, [col_chav], aba).iterrows():
            lista.append({
                'aba': aba, 'linha': int(row.get('_linha_excel', 0)),
                'coluna': col_chav, 'tipo': 'DUPLICATA',
                'severidade': Status.CRITICA,
                'valor': str(row.get(col_chav, '')),
                'descricao': f"Duplicata em '{col_chav}'",
                'impacto_rs': 0,
            })

    def _coletar_outliers(self, df, col_val, aba, lista):
        n = self.cfg.get('auditoria', {}).get('outlier_desvios', 3.0)
        for _, row in Auditor.detectar_outliers(df, col_val, n_desvios=n, aba=aba).iterrows():
            lista.append({
                'aba': aba, 'linha': int(row.get('_linha_excel', 0)),
                'coluna': col_val, 'tipo': 'OUTLIER',
                'severidade': Status.MEDIA,
                'valor': str(row.get(col_val, '')),
                'descricao': f"Outlier ±{row.get('_desvio_padrao','?')}σ",
                'impacto_rs': 0,
            })

    def _calcular_aging(self, df, col_venc, col_val):
        if col_venc in df.columns and col_val in df.columns:
            try:
                return AnalistaFinanceiro.calcular_aging(df, col_venc, col_val)
            except (KeyError, ValueError, TypeError) as e:
                logger.debug("Aging ignorado: %s", e)
        return None

    def _construir_dre(self, df, col_cat, col_val):
        if col_cat in df.columns and col_val in df.columns:
            try:
                return AnalistaFinanceiro.construir_dre(df, col_cat, col_val)
            except (KeyError, ValueError, AttributeError) as e:
                logger.debug("DRE ignorado: %s", e)
        return None

    def _calcular_pareto(self, df, col_ent, col_val):
        if col_ent in df.columns and col_val in df.columns:
            try:
                return AnalistaComercial.pareto(df, col_ent, col_val)
            except (KeyError, ValueError, ZeroDivisionError) as e:
                logger.debug("Pareto ignorado: %s", e)
        return None

    def _calcular_ticket(self, df, col_val, col_ent):
        if col_val in df.columns:
            try:
                g = col_ent if col_ent in df.columns else None
                return AnalistaComercial.ticket_medio(df, col_val, g)
            except (KeyError, ValueError, TypeError) as e:
                logger.debug("Ticket ignorado: %s", e)
        return None

    def _montar_metricas(self, df, df_audit, col_val, criticos) -> dict:
        metricas = {}
        if col_val in df.columns:
            total = pd.to_numeric(df[col_val], errors='coerce').sum()
            media = pd.to_numeric(df[col_val], errors='coerce').mean()
            metricas['Total Geral']  = {'valor': total, 'tipo': 'moeda', 'status': Status.OK}
            metricas['Ticket Médio'] = {'valor': media, 'tipo': 'moeda', 'status': Status.OK}
        metricas['Total de Registros']  = {'valor': len(df),  'tipo': 'numero', 'status': Status.OK}
        metricas['Problemas Críticos']  = {
            'valor': criticos, 'tipo': 'numero',
            'status': Status.OK if criticos == 0 else Status.DIVERGENTE,
            'obs': f"{len(df_audit)} alertas no total",
        }
        return metricas

    # ── Mapa de soluções por tipo de problema ─────────────────────

    _SOLUCOES = {
        'DUPLICATA': (
            "Remover registros duplicados",
            "Verifique qual linha deve ser mantida e exclua as demais. "
            "No Excel: Dados → Remover Duplicatas. Confirme antes qual versão "
            "do registro é a correta (ex.: a mais recente ou a de maior valor).",
        ),
        'OUTLIER': (
            "Verificar valor atípico",
            "O valor está muito acima ou abaixo da média histórica. "
            "Confira se houve erro de digitação (ex.: 1.000 digitado como 100.000), "
            "separador decimal errado ou lançamento em duplicidade com valor somado.",
        ),
        'CAMPO_VAZIO': (
            "Preencher campo obrigatório",
            "Este campo é obrigatório e não pode ficar em branco. "
            "Localize a linha indicada, preencha com o valor correto e reimporte o arquivo. "
            "Sem esta informação o registro não será processado corretamente.",
        ),
        'NUMERO_COMO_TEXTO': (
            "Converter coluna para formato numérico",
            "A coluna contém números armazenados como texto (geralmente por importação de ERP). "
            "No Excel: selecione a coluna → clique no aviso amarelo → 'Converter em Número'. "
            "Ou use a fórmula =VALOR(A1) em uma coluna auxiliar.",
        ),
        'DATAS_FORMATO_MISTO': (
            "Padronizar formato de datas",
            "A coluna mistura formatos de data (ex.: DD/MM/AAAA e AAAA-MM-DD). "
            "Padronize todas as datas para DD/MM/AAAA antes de reimportar. "
            "No Excel: selecione a coluna → Formatar Células → Data → escolha o padrão.",
        ),
        'COLUNA_VAZIA': (
            "Verificar coluna completamente vazia",
            "Esta coluna não possui nenhum dado. Verifique se o nome da coluna está "
            "correto no arquivo de origem ou se os dados foram exportados corretamente do sistema.",
        ),
        'INCONSISTENCIA_TEMPORAL': (
            "Corrigir inconsistência de datas",
            "Há datas fora de ordem ou incoerentes (ex.: vencimento anterior à emissão). "
            "Revise os campos de Data e Vencimento nas linhas indicadas.",
        ),
    }

    _COR_SEV = {
        'CRÍTICA': ('#FEE2E2', '#991B1B', '🔴'),
        'ALTA':    ('#FFF0E6', '#7C2D12', '🟠'),
        'MÉDIA':   ('#FEF3C7', '#92400E', '🟡'),
        'BAIXA':   ('#D1FAE5', '#065F46', '🟢'),
    }

    def _gerar_relatorio_acoes(self, resultado: dict, df_audit: pd.DataFrame) -> str:
        """Gera relatório HTML com problemas encontrados e sugestões de correção."""
        from datetime import datetime as _dt
        agora   = _dt.now().strftime('%d/%m/%Y %H:%M')
        arquivo = Path(resultado['arquivo_origem']).name
        criticos = resultado['criticos']
        total    = resultado['total_problemas']

        status_cor = '#C0392B' if criticos > 0 else '#E8A020'
        status_txt = f"{criticos} problema(s) CRÍTICO(S) — ação imediata necessária" if criticos > 0 else f"{total} aviso(s) — revisar antes de prosseguir"

        itens_html = ''
        for _, r in df_audit.iterrows():
            sev   = str(r.get('Severidade', 'MÉDIA'))
            tipo  = str(r.get('Tipo', ''))
            col   = str(r.get('Coluna', ''))
            desc  = str(r.get('Descrição', ''))
            linha = r.get('Linha', '')
            if isinstance(linha, list):
                linha = ', '.join(str(x) for x in linha[:5])

            fundo, texto, emoji = self._COR_SEV.get(sev, ('#FEF3C7', '#92400E', '🟡'))
            titulo_sol, detalhe_sol = self._SOLUCOES.get(tipo, (
                "Revisar manualmente",
                "Verifique o campo indicado e corrija conforme as regras do negócio.",
            ))

            import html as _html
            itens_html += f"""
  <div style="border:1px solid #DDE6F0;border-radius:10px;margin-bottom:16px;overflow:hidden">
    <div style="background:{fundo};padding:14px 18px;display:flex;align-items:center;gap:10px">
      <span style="font-size:18px">{emoji}</span>
      <div style="flex:1">
        <span style="font-size:11px;font-weight:700;color:{texto};text-transform:uppercase;letter-spacing:.5px">{_html.escape(sev)}</span>
        <span style="margin:0 8px;color:#9BA8B5">|</span>
        <span style="font-size:13px;font-weight:600;color:#0D1B2A">{_html.escape(tipo)}</span>
        {f'<span style="margin:0 8px;color:#9BA8B5">|</span><span style="font-size:12px;color:#4A6080">Coluna: <b>{_html.escape(col)}</b></span>' if col else ''}
        {f'<span style="margin:0 8px;color:#9BA8B5">|</span><span style="font-size:12px;color:#4A6080">Linha(s): {_html.escape(str(linha))}</span>' if linha else ''}
      </div>
    </div>
    <div style="padding:14px 18px;background:white">
      <p style="color:#4A6080;font-size:13px;margin-bottom:12px">{_html.escape(desc)}</p>
      <div style="background:#F5F8FC;border-left:3px solid #1A3556;padding:12px 16px;border-radius:4px">
        <p style="font-size:11px;font-weight:700;color:#1A3556;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px">✅ Como corrigir: {_html.escape(titulo_sol)}</p>
        <p style="font-size:13px;color:#2C5282;line-height:1.6">{_html.escape(detalhe_sol)}</p>
      </div>
    </div>
  </div>"""

        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Relatório de Ações — {_html.escape(arquivo)}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Inter',Arial,sans-serif;background:#EEF2F7;color:#0D1B2A;font-size:14px;line-height:1.6;-webkit-font-smoothing:antialiased}}
</style>
</head>
<body>
<div style="background:linear-gradient(135deg,#0D1B2A,#1A3556);color:white;padding:22px 36px;display:flex;justify-content:space-between;align-items:center">
  <div>
    <div style="font-size:11px;opacity:.6;text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px">Toolkit Financeiro</div>
    <h1 style="font-size:18px;font-weight:700">Relatório de Ações Corretivas</h1>
  </div>
  <div style="text-align:right;font-size:11.5px;opacity:.7">
    Arquivo: {_html.escape(arquivo)}<br>Gerado em: {agora}
  </div>
</div>

<div style="max-width:860px;margin:28px auto;padding:0 20px">

  <div style="background:{status_cor};color:white;border-radius:10px;padding:16px 20px;margin-bottom:24px;font-weight:600;font-size:14px">
    ⚠ {_html.escape(status_txt)}
  </div>

  {itens_html}

  <div style="background:white;border-radius:10px;padding:20px;border:1px solid #DDE6F0;margin-top:24px">
    <p style="font-size:12px;color:#9BA8B5">
      Após corrigir os itens acima, reimporte o arquivo em <code>pasta_entrada/</code> para reprocessamento automático.<br>
      O relatório completo de auditoria está disponível no arquivo HTML principal gerado junto a este.
    </p>
  </div>

</div>
<div style="text-align:center;font-size:11px;color:#9BA8B5;padding:24px;border-top:1px solid #DDE6F0;margin-top:8px">
  Toolkit Financeiro &bull; {agora} &bull; <strong>Luan Guilherme Lourenço</strong>
</div>
</body></html>"""

    def _gerar_briefing(self, df, diagnostico, df_auditoria, df_dre,
                        df_aging, df_pareto, df_ticket,
                        df_fluxo_m=None) -> str:
        """Gera texto compacto com os achados principais para envio ao Claude API."""
        linhas = [
            f"# BRIEFING FINANCEIRO — {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            f"Arquivo: {diagnostico['arquivo']}",
            f"Total de registros: {diagnostico['total_registros']:,}",
            "",
        ]
        if diagnostico.get('problemas_formato'):
            linhas.append(f"## Problemas de formato ({len(diagnostico['problemas_formato'])})")
            for p in diagnostico['problemas_formato']:
                linhas.append(f"- [{p['severidade']}] {p['descricao']}")
            linhas.append("")
        if len(df_auditoria):
            linhas.append(f"## Auditoria — {len(df_auditoria)} problemas encontrados")
            for sev in [Status.CRITICA, Status.ALTA, Status.MEDIA, Status.BAIXA]:
                subset = df_auditoria[df_auditoria['Severidade'] == sev]
                if len(subset):
                    linhas.append(f"\n### {sev} ({len(subset)})")
                    for _, row in subset.head(10).iterrows():
                        linhas.append(f"- Linha {row.get('Linha','?')} | {row.get('Coluna','?')} | {row.get('Descrição','')}")
            linhas.append("")
        if df_dre is not None and len(df_dre):
            linhas.append("## DRE Resumido")
            for _, row in df_dre.iterrows():
                av = f" ({row['AV_%']:.1f}%)" if 'AV_%' in row and pd.notna(row.get('AV_%')) else ""
                linhas.append(f"  {row['Linha_DRE']:<40} R$ {row['Valor_RS']:>15,.2f}{av}")
            linhas.append("")
        if df_aging is not None and len(df_aging):
            linhas.append("## Aging de Recebíveis")
            for _, row in df_aging.iterrows():
                linhas.append(
                    f"  {row['Faixa_Aging']:<25} {row['Quantidade']:>5} itens"
                    f"  R$ {row['Total_RS']:>12,.2f}  ({row.get('Percentual',0):.1f}%)"
                )
            linhas.append("")
        if df_pareto is not None and len(df_pareto):
            linhas.append("## Top 5 por Faturamento (Pareto)")
            col_entidade = df_pareto.columns[0]
            for _, row in df_pareto.head(5).iterrows():
                linhas.append(
                    f"  #{int(row['Ranking'])} {str(row[col_entidade]):<30}"
                    f"  R$ {row['Total_RS']:>12,.2f}  ({row['Percentual']:.1f}%)"
                )
            linhas.append("")
        if df_ticket is not None and len(df_ticket) and 'Ticket_Medio_RS' in df_ticket.columns:
            linhas.append("## Ticket Médio")
            for _, row in df_ticket.head(5).iterrows():
                linhas.append(
                    f"  Ticket médio: R$ {row['Ticket_Medio_RS']:,.2f}"
                    f" | {int(row.get('Transações', 0))} transações"
                )
            linhas.append("")
        # ── Fluxo Mensal ──────────────────────────────────────────
        if df_fluxo_m is not None and len(df_fluxo_m):
            linhas.append("## Fluxo por Mês")
            cols_fluxo = df_fluxo_m.columns.tolist()
            col_per  = next((c for c in cols_fluxo if 'periodo' in c.lower() or 'period' in c.lower()), cols_fluxo[0])
            col_rec  = next((c for c in cols_fluxo if 'receita' in c.lower()), None)
            col_desp = next((c for c in cols_fluxo if 'despesa' in c.lower()), None)
            col_res  = next((c for c in cols_fluxo if 'resultado' in c.lower()), None)
            for _, row in df_fluxo_m.tail(12).iterrows():
                partes = [f"  {row[col_per]}"]
                if col_rec:  partes.append(f"Rec R$ {row[col_rec]:>12,.2f}")
                if col_desp: partes.append(f"Desp R$ {row[col_desp]:>12,.2f}")
                if col_res:
                    res = row[col_res]
                    sinal = '+' if res >= 0 else ''
                    partes.append(f"Resultado {sinal}R$ {res:,.2f}")
                linhas.append("  |  ".join(partes))
            linhas.append("")

        # ── Score Financeiro (0–100) ───────────────────────────
        try:
            # Margem líquida (30 pts)
            col_val_df = 'Valor' if 'Valor' in df.columns else df.columns[0]
            nums = pd.to_numeric(df[col_val_df], errors='coerce').dropna()
            receita = nums[nums > 0].sum()
            despesa = nums[nums < 0].abs().sum()
            margem  = (receita - despesa) / receita * 100 if receita else 0
            pts_m   = 30 if margem >= 30 else (20 if margem >= 15 else (10 if margem >= 5 else 0))

            # Inadimplência aging (25 pts)
            pts_a = 0
            if df_aging is not None and len(df_aging):
                total_ag = df_aging['Total_RS'].sum() if 'Total_RS' in df_aging.columns else 0
                col_faixa = next((c for c in df_aging.columns if 'faixa' in c.lower()), None)
                if col_faixa and 'Total_RS' in df_aging.columns:
                    vencido  = df_aging[~df_aging[col_faixa].str.contains('vencer|Sem', na=False)]['Total_RS'].sum()
                    pct_venc = vencido / total_ag * 100 if total_ag > 0 else 0
                    pts_a = 25 if pct_venc == 0 else (18 if pct_venc < 10 else (10 if pct_venc < 25 else 0))

            # Concentração Pareto (20 pts)
            pts_p = 20
            if df_pareto is not None and len(df_pareto) >= 3 and 'Percentual' in df_pareto.columns:
                top3_pct = df_pareto.head(3)['Percentual'].sum()
                pts_p = 20 if top3_pct < 40 else (12 if top3_pct < 60 else (6 if top3_pct < 80 else 0))

            # Auditoria críticos (25 pts)
            criticos = len(df_auditoria[df_auditoria['Severidade'] == 'CRÍTICA']) if len(df_auditoria) else 0
            pts_aud  = 25 if criticos == 0 else (18 if criticos <= 2 else (10 if criticos <= 5 else 0))

            score = pts_m + pts_a + pts_p + pts_aud
            classe = 'EXCELENTE' if score >= 80 else ('MODERADA' if score >= 60 else 'ATENÇÃO')
            linhas.append(f"## Score Financeiro: {score}/100 — {classe}")
            linhas.append(f"  Margem ({pts_m}/30) | Inadimplência ({pts_a}/25) | Concentração ({pts_p}/20) | Auditoria ({pts_aud}/25)")
            linhas.append(f"  Margem líquida: {margem:.1f}% | Críticos auditoria: {criticos}")
            linhas.append("")
        except Exception as _e:
            logging.getLogger(__name__).warning("Score financeiro não calculado: %s", _e)

        linhas += [
            "---",
            "Analise os dados acima e indique:",
            "1. Quais inconsistências são mais críticas?",
            "2. O que o DRE e o fluxo mensal indicam sobre a saúde financeira?",
            "3. Quais ações recomenda com base no aging e no score?",
            "4. Existe concentração de risco em poucos clientes/fornecedores?",
        ]
        return '\n'.join(linhas)

    def _enviar_email(self, resultado: dict, df_audit: pd.DataFrame):
        cfg_email = self.cfg.get('email', {})
        if not cfg_email.get('ativo', False):
            return
        try:
            smtp   = cfg_email['smtp_servidor']
            porta  = cfg_email.get('smtp_porta', 587)
            rem    = cfg_email['remetente']
            senha = os.environ.get('EMAIL_SENHA', '')
            if not senha and cfg_email.get('senha'):
                logger.warning(
                    "Senha de e-mail definida em config.yaml — use a variável de ambiente "
                    "EMAIL_SENHA para evitar expor credenciais no repositório."
                )
                senha = cfg_email['senha']
            dests = cfg_email.get('destinatarios', [])
            if not dests:
                logger.warning("Email ativo mas lista de destinatários vazia.")
                return
            if not senha:
                return

            assunto = f"{cfg_email.get('assunto_prefixo','[Toolkit]')} {resultado['total_problemas']} alertas — {Path(resultado['arquivo_origem']).name}"
            assunto = assunto.replace('\r', ' ').replace('\n', ' ')

            # Corpo do e-mail
            criticos_html = ''
            for _, r in df_audit[df_audit['Severidade'] == str(Status.CRITICA)].head(10).iterrows():
                tipo = _html_mod.escape(str(r.get('Tipo', '')))
                desc = _html_mod.escape(str(r.get('Descrição', '')))
                criticos_html += f"<li><b>{tipo}</b> — {desc}</li>"

            corpo = f"""
<h2>Alerta Automático — Toolkit Financeiro</h2>
<p><b>Arquivo:</b> {Path(resultado['arquivo_origem']).name}</p>
<p><b>Processado em:</b> {resultado['timestamp']}</p>
<p><b>Problemas críticos:</b> {resultado['criticos']}</p>
<p><b>Total de alertas:</b> {resultado['total_problemas']}</p>
<hr>
<h3>Problemas Críticos:</h3>
<ul>{criticos_html}</ul>
<hr>
<p>Abra o relatório HTML para detalhes completos.</p>
"""
            msg = MIMEMultipart('alternative')
            msg['Subject'] = assunto
            msg['From']    = rem
            msg['To']      = ', '.join(dests)
            msg.attach(MIMEText(corpo, 'html'))

            # Port 465 = SMTP_SSL (implicit TLS); port 587/25 = STARTTLS
            use_ssl = (porta == 465)
            ctx = ssl.create_default_context()

            max_tentativas = 3
            for tentativa in range(1, max_tentativas + 1):
                try:
                    if use_ssl:
                        with smtplib.SMTP_SSL(smtp, porta, context=ctx, timeout=10) as server:
                            server.login(rem, senha)
                            server.sendmail(rem, dests, msg.as_string())
                    else:
                        with smtplib.SMTP(smtp, porta, timeout=10) as server:
                            server.starttls(context=ctx)
                            server.login(rem, senha)
                            server.sendmail(rem, dests, msg.as_string())
                    logger.info("E-mail de alerta enviado para %s", dests)
                    return
                except smtplib.SMTPAuthenticationError as e:
                    logger.error("Falha de autenticação SMTP: %s", e)
                    return
                except (smtplib.SMTPConnectError, smtplib.SMTPException,
                        OSError, ConnectionRefusedError) as e:
                    if tentativa < max_tentativas:
                        espera = 2 ** tentativa
                        logger.warning(
                            "E-mail: tentativa %d/%d falhou (%s). Aguardando %ds...",
                            tentativa, max_tentativas, e, espera,
                        )
                        time.sleep(espera)
                    else:
                        logger.error(
                            "Falha ao enviar e-mail após %d tentativas: %s",
                            max_tentativas, e,
                        )
        except KeyError as e:
            logger.error("Configuração de e-mail incompleta: %s", e)


# ══════════════════════════════════════════════════════════════════
# OBSERVADOR DE PASTA (modo contínuo)
# ══════════════════════════════════════════════════════════════════

class ObservadorPasta:
    """Monitora a pasta de entrada e processa arquivos novos."""

    def __init__(self, processador: ProcessadorArquivo, pasta: str):
        self.processador = processador
        self.pasta       = Path(pasta)
        self.pasta.mkdir(parents=True, exist_ok=True)
        self._vistos: set = set()
        self._estados_pendentes: dict = {}  # arquivo.name → (size, mtime)

    def varrer_uma_vez(self):
        """Verifica a pasta e processa arquivos ainda não processados."""
        pasta_real = self.pasta.resolve()
        # Clean up _estados_pendentes for files that no longer exist
        arquivos_atuais = {
            f.name for f in self.pasta.iterdir()
            if f.suffix.lower() in ProcessadorArquivo.EXTENSOES_SUPORTADAS
        }
        for nome in list(self._estados_pendentes):
            if nome not in arquivos_atuais:
                del self._estados_pendentes[nome]
        for arquivo in self.pasta.iterdir():
            try:
                # Bloqueia symlinks que apontam para fora da pasta monitorada
                arquivo.resolve().relative_to(pasta_real)
            except ValueError:
                logger.warning("Symlink fora da pasta de entrada ignorado: %s", arquivo)
                continue
            if arquivo.suffix.lower() in ProcessadorArquivo.EXTENSOES_SUPORTADAS:
                if arquivo.name not in self._vistos:
                    # Verifica estabilidade: aguarda o arquivo parar de ser copiado
                    try:
                        estado_atual = (arquivo.stat().st_size, arquivo.stat().st_mtime)
                    except OSError:
                        continue
                    if self._estados_pendentes.get(arquivo.name) != estado_atual:
                        self._estados_pendentes[arquivo.name] = estado_atual
                        continue  # ainda sendo copiado — tenta na próxima varredura
                    self._estados_pendentes.pop(arquivo.name, None)
                    # Marca como visto antes de processar para evitar loop infinito.
                    # Para reprocessar, renomeie ou reimporte o arquivo.
                    self._vistos.add(arquivo.name)
                    resultado = self.processador.processar(str(arquivo))
                    if resultado.get('status') == 'ERRO':
                        err = resultado.get('erro', '')
                        # Erro de I/O irrecuperável: remove dos vistos para retry.
                        if any(kw in err for kw in ('PermissionError', 'OSError', 'IOError')):
                            self._vistos.discard(arquivo.name)
                            logger.warning("Arquivo %s será reprocessado na próxima varredura.", arquivo.name)

    def monitorar(self, intervalo: int = 5):
        """Loop contínuo: verifica a pasta a cada N segundos."""
        logger.info("Monitorando pasta: %s (intervalo: %ds)", self.pasta, intervalo)
        logger.info("Coloque arquivos em '%s' para processar automaticamente.", self.pasta)
        logger.info("Pressione Ctrl+C para parar.\n")
        try:
            while True:
                self.varrer_uma_vez()
                time.sleep(intervalo)
        except KeyboardInterrupt:
            logger.info("Motor encerrado pelo usuário.")


# ══════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='Motor Autônomo — Toolkit Financeiro')
    parser.add_argument('--config',   default='config.yaml',   help='Caminho do config.yaml')
    parser.add_argument('--once',     action='store_true',      help='Processar uma vez e sair')
    parser.add_argument('--arquivo',  default=None,             help='Processar arquivo específico')
    parser.add_argument('--intervalo',type=int, default=5,      help='Intervalo de monitoramento (segundos)')
    args = parser.parse_args()

    cfg          = carregar_config(args.config)

    logger.info("=" * 55)
    logger.info("Toolkit Financeiro — Motor Autônomo")
    logger.info("Powered by Luan Guilherme Lourenço")
    logger.info("=" * 55)

    processador  = ProcessadorArquivo(cfg)
    pasta_entrada = cfg.get('pastas', {}).get('entrada', 'pasta_entrada')

    if args.arquivo:
        # Modo: arquivo específico
        resultado = processador.processar(args.arquivo)
        logger.info("HTML:    %s", resultado['html'])
        logger.info("Excel:   %s", resultado['xlsx'])
        if resultado.get('analise'):
            logger.info("Análise: %s", resultado['analise'])
        logger.info("Críticos: %d | Total alertas: %d", resultado['criticos'], resultado['total_problemas'])

    elif args.once:
        # Modo: varrer pasta uma vez
        obs = ObservadorPasta(processador, pasta_entrada)
        obs.varrer_uma_vez()

    else:
        # Modo padrão: monitorar continuamente
        obs = ObservadorPasta(processador, pasta_entrada)
        obs.monitorar(intervalo=args.intervalo)


if __name__ == '__main__':
    main()
