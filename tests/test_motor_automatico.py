"""
Testes para motor_automatico.py — ProcessadorArquivo e helpers

Execução:
    pytest tests/test_motor_automatico.py -v
"""
import logging
import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import MagicMock, patch

from motor_automatico import ProcessadorArquivo


@pytest.fixture
def config_basico(tmp_path):
    return {
        'pastas': {
            'saida': str(tmp_path / 'saida'),
            'log': str(tmp_path / 'log.txt'),
        },
        'colunas': {
            'valor': 'Valor',
            'categoria': 'Categoria',
            'data': 'Data',
            'vencimento': 'Vencimento',
            'chave': 'NF',
            'entidade': 'Cliente',
        },
        'auditoria': {'outlier_desvios': 3.0},
        'email': {'ativo': False},
    }


@pytest.fixture
def processador(config_basico):
    return ProcessadorArquivo(config_basico)


# ── Testes de processamento de arquivo ────────────────────────────

def test_processar_arquivo_inexistente(processador):
    resultado = processador.processar('/caminho/que/nao/existe.xlsx')
    assert resultado['status'] == 'ERRO'
    assert resultado['erro'] is not None


def test_processar_dados_vazios(processador):
    with patch('motor_automatico.Leitor.ler_arquivo') as mock_ler:
        mock_ler.return_value = {
            'dados': {},
            'diagnostico': {'arquivo': 'vazio.xlsx', 'total_registros': 0, 'problemas_formato': []},
        }
        resultado = processador.processar('vazio.xlsx')
    assert resultado['status'] == 'ERRO'
    assert resultado['erro'] is not None


# ── Testes de envio de email ──────────────────────────────────────

def test_enviar_email_desativado(processador):
    resultado_fake = {'arquivo_origem': 'x.xlsx', 'total_problemas': 1, 'criticos': 1, 'timestamp': '20240101'}
    df_audit = pd.DataFrame(columns=['Severidade', 'Tipo', 'Descrição'])
    with patch('smtplib.SMTP') as mock_smtp:
        processador._enviar_email(resultado_fake, df_audit)
        mock_smtp.assert_not_called()


def test_enviar_email_sem_destinatarios(config_basico):
    cfg = dict(config_basico)
    cfg['email'] = {'ativo': True, 'smtp_servidor': 'smtp.test.com', 'remetente': 'a@b.com', 'destinatarios': []}
    proc = ProcessadorArquivo(cfg)
    resultado_fake = {'arquivo_origem': 'x.xlsx', 'total_problemas': 1, 'criticos': 1, 'timestamp': '20240101'}
    df_audit = pd.DataFrame(columns=['Severidade', 'Tipo', 'Descrição'])
    with patch('smtplib.SMTP') as mock_smtp:
        proc._enviar_email(resultado_fake, df_audit)
        mock_smtp.assert_not_called()


def test_enviar_email_credencial_warning_via_config(config_basico, caplog):
    cfg = dict(config_basico)
    cfg['email'] = {
        'ativo': True,
        'smtp_servidor': 'smtp.test.com',
        'smtp_porta': 587,
        'remetente': 'a@b.com',
        'senha': 'senha_secreta_config',
        'destinatarios': ['dest@exemplo.com'],
    }
    proc = ProcessadorArquivo(cfg)
    resultado_fake = {'arquivo_origem': 'x.xlsx', 'total_problemas': 1, 'criticos': 1, 'timestamp': '20240101'}
    df_audit = pd.DataFrame(columns=['Severidade', 'Tipo', 'Descrição'])
    with patch('smtplib.SMTP') as mock_smtp, patch.dict('os.environ', {}, clear=True):
        mock_smtp.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
        with caplog.at_level(logging.WARNING, logger='motor_automatico'):
            proc._enviar_email(resultado_fake, df_audit)
    assert any('config.yaml' in rec.message for rec in caplog.records)


def test_enviar_email_smtp_timeout_configurado(config_basico):
    cfg = dict(config_basico)
    cfg['email'] = {
        'ativo': True,
        'smtp_servidor': 'smtp.test.com',
        'smtp_porta': 587,
        'remetente': 'a@b.com',
        'senha': 'qualquer',
        'destinatarios': ['dest@exemplo.com'],
    }
    proc = ProcessadorArquivo(cfg)
    resultado_fake = {'arquivo_origem': 'x.xlsx', 'total_problemas': 1, 'criticos': 1, 'timestamp': '20240101'}
    df_audit = pd.DataFrame(columns=['Severidade', 'Tipo', 'Descrição'])
    chamadas = []

    class FakeSMTP:
        def __init__(self, host, port, timeout=None):
            chamadas.append({'host': host, 'port': port, 'timeout': timeout})

        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self, **kwargs): pass
        def login(self, *a): pass
        def sendmail(self, *a): pass

    with patch('smtplib.SMTP', FakeSMTP), patch.dict('os.environ', {'EMAIL_SENHA': 'env_senha'}):
        proc._enviar_email(resultado_fake, df_audit)

    assert chamadas, "SMTP não foi chamado"
    assert chamadas[0]['timeout'] == 10
