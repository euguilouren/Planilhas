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
import sys
import time
import logging
import smtplib
import argparse
import traceback
from difflib                import get_close_matches
from email.mime.text        import MIMEText
from email.mime.multipart   import MIMEMultipart
from datetime               import datetime
from pathlib                import Path

import yaml
import pandas as pd

from toolkit_financeiro import (
    Leitor, Auditor, AnalistaFinanceiro, AnalistaComercial,
    MontadorPlanilha, Verificador, Util, Status, validar_config
)
from relatorio_html import GeradorHTML

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
    with open(caminho, encoding='utf-8') as f:
        cfg = yaml.safe_load(f) or {}
    avisos = validar_config(cfg)
    for aviso in avisos:
        logger.warning("config.yaml: %s", aviso)
    if cfg.get('validacao', {}).get('falhar_em_config_invalida', False) and avisos:
        raise SystemExit(f"Configuração inválida ({len(avisos)} erros). Corrija config.yaml.")
    return cfg


# ══════════════════════════════════════════════════════════════════
# PROCESSADOR PRINCIPAL
# ══════════════════════════════════════════════════════════════════

class ProcessadorArquivo:
    """Processa um arquivo financeiro e gera relatório HTML + Excel."""

    EXTENSOES_SUPORTADAS = {'.xlsx', '.xls', '.xlsm', '.csv', '.tsv'}

    def __init__(self, config: dict):
        self.cfg      = config
        self.cols     = config.get('colunas', {})
        self.gerador  = GeradorHTML(config)
        self.pasta_saida = Path(config.get('pastas', {}).get('saida', 'pasta_saida'))
        self.pasta_saida.mkdir(parents=True, exist_ok=True)

        # Configurar logging para arquivo
        log_path = config.get('pastas', {}).get('log', str(self.pasta_saida / 'log.txt'))
        fh = logging.FileHandler(log_path, encoding='utf-8')
        fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
        logger.addHandler(fh)

    @staticmethod
    def _validar_caminho_arquivo(caminho: str) -> Path:
        """Resolve o caminho e bloqueia symlinks que escapam da pasta monitorada."""
        try:
            p = Path(caminho).resolve()
        except (OSError, ValueError) as exc:
            raise ValueError(f"Caminho inválido: {caminho}") from exc
        if p.suffix.lower() not in ProcessadorArquivo.EXTENSOES_SUPORTADAS:
            raise ValueError(f"Extensão '{p.suffix}' não suportada.")
        return p

    def processar(self, caminho_arquivo: str) -> dict:
        """
        Pipeline completo: lê → audita → analisa → gera HTML + Excel.
        Retorna dict com caminhos dos arquivos gerados e resumo.
        """
        caminho_arquivo = str(self._validar_caminho_arquivo(caminho_arquivo))
        nome_base = Path(caminho_arquivo).stem
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        prefixo   = f"{nome_base}_{timestamp}"

        logger.info("=" * 55)
        logger.info("Processando: %s", caminho_arquivo)

        resultado = {
            'arquivo_origem':  caminho_arquivo,
            'timestamp':       timestamp,
            'html':            None,
            'xlsx':            None,
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
            total_criticos = len(df_auditoria[df_auditoria['Severidade'] == Status.CRITICA]) if len(df_auditoria) else 0
            resultado['criticos']        = total_criticos
            resultado['total_problemas'] = len(df_auditoria)
            logger.info("      %d problemas (%d críticos)", len(df_auditoria), total_criticos)

            # ── 3. Análises ──────────────────────────────────────
            logger.info("[3/5] Análises financeiras...")
            df_aging  = self._calcular_aging(df, col_venc, col_val)
            df_dre    = self._construir_dre(df, col_cat, col_val)
            df_pareto = self._calcular_pareto(df, col_ent, col_val)
            df_ticket = self._calcular_ticket(df, col_val, col_ent)

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
            )
            caminho_html = self.pasta_saida / f"relatorio_{prefixo}.html"
            caminho_html.write_text(html, encoding='utf-8')
            resultado['html'] = str(caminho_html)
            logger.info("      HTML: %s", caminho_html)

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

            # ── Alerta por e-mail ─────────────────────────────────
            if total_criticos > 0:
                resultado['status'] = 'ALERTA'
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
        """Detecta ERPs por correspondência exata ou fuzzy (difflib) nas colunas."""
        from base_conhecimento import MAPAS_ERP
        cols_upper = list(df.columns.str.upper())
        sinais = {
            'TOTVS':   ['E1_NUM', 'E1_CLIENTE', 'E1_VALOR'],
            'OMIE':    ['NUMERO_DOCUMENTO', 'NOME_CLIENTE', 'VALOR_DOCUMENTO'],
            'DOMINIO': ['HISTÓRICO', 'SAL. BASE'],
            'QUESTOR': ['DT_LANCTO', 'VL_LANCTO'],
            'SAP_B1':  ['DOCNUM', 'CARDCODE', 'DOCTOTAL'],
        }
        for erp, campos in sinais.items():
            correspondencias = sum(
                1 for campo in campos
                if campo in cols_upper
                or get_close_matches(campo, cols_upper, n=1, cutoff=0.85)
            )
            if correspondencias >= 2:
                logger.info("      ERP detectado (fuzzy): %s", erp)
                if erp in MAPAS_ERP:
                    return df.rename(columns=MAPAS_ERP[erp])
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

    def _enviar_email(self, resultado: dict, df_audit: pd.DataFrame):
        cfg_email = self.cfg.get('email', {})
        if not cfg_email.get('ativo', False):
            return
        try:
            smtp   = cfg_email['smtp_servidor']
            porta  = cfg_email.get('smtp_porta', 587)
            rem    = cfg_email['remetente']
            senha = os.environ.get('EMAIL_SENHA', '')
            if not senha:
                senha = cfg_email.get('senha', '')
                if senha:
                    logger.warning("EMAIL_SENHA lida do config.yaml — prefira a variável de ambiente EMAIL_SENHA")
            dests = cfg_email.get('destinatarios', [])
            if not dests:
                logger.warning("Email ativo mas lista de destinatários vazia.")
                return
            if not senha:
                return

            assunto = f"{cfg_email.get('assunto_prefixo','[Toolkit]')} {resultado['total_problemas']} alertas — {Path(resultado['arquivo_origem']).name}"

            # Corpo do e-mail
            criticos_html = ''
            for _, r in df_audit[df_audit['Severidade'] == Status.CRITICA].head(10).iterrows():
                criticos_html += f"<li><b>{r.get('Tipo','')}</b> — {r.get('Descrição','')}</li>"

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

            max_tentativas = 3
            for tentativa in range(1, max_tentativas + 1):
                try:
                    with smtplib.SMTP(smtp, porta, timeout=10) as server:
                        server.starttls()
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

    def varrer_uma_vez(self):
        """Verifica a pasta e processa arquivos ainda não processados."""
        pasta_real = self.pasta.resolve()
        for arquivo in self.pasta.iterdir():
            try:
                # Bloqueia symlinks que apontam para fora da pasta monitorada
                arquivo.resolve().relative_to(pasta_real)
            except ValueError:
                logger.warning("Symlink fora da pasta de entrada ignorado: %s", arquivo)
                continue
            if arquivo.suffix.lower() in ProcessadorArquivo.EXTENSOES_SUPORTADAS:
                if arquivo.name not in self._vistos:
                    self._vistos.add(arquivo.name)
                    self.processador.processar(str(arquivo))

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
        logger.info("HTML:  %s", resultado['html'])
        logger.info("Excel: %s", resultado['xlsx'])
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
