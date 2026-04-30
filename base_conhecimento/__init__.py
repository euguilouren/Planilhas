"""
Mapeamentos de ERP para normalização de colunas.

Uso:
    from base_conhecimento import MAPAS_ERP, ASSINATURAS_ERP, detectar_erp

    erp = detectar_erp(df)
    if erp in MAPAS_ERP:
        df = df.rename(columns=MAPAS_ERP[erp]['colunas'])
"""

from typing import Dict, Optional
import pandas as pd


# Mapeamentos: coluna-original → coluna-padrão do toolkit
# Cada entrada tem:
#   'sinais'  : colunas que identificam este ERP (mínimo 2 para confirmar)
#   'colunas' : mapeamento renomeação col_erp → col_padrão
MAPAS_ERP: Dict[str, dict] = {

    # ── TOTVS Protheus (SE1 / Contas a Receber) ──────────────
    'TOTVS': {
        'sinais': ['E1_NUM', 'E1_CLIENTE', 'E1_VALOR'],
        'colunas': {
            'E1_NUM':     'NF',
            'E1_NOMCLI':  'Cliente',
            'E1_CLIENTE': 'Cod_Cliente',
            'E1_VALOR':   'Valor',
            'E1_SALDO':   'Saldo',
            'E1_VENCTO':  'Vencimento',
            'E1_EMISSAO': 'Data',
            'E1_BAIXA':   'Data_Baixa',
            'E1_SITUACA': 'Status',
            'E1_TIPO':    'Tipo',
            'E1_PREFIXO': 'Prefixo',
        },
    },

    # ── TOTVS RM ─────────────────────────────────────────────
    'TOTVS_RM': {
        'sinais': ['IDLAN', 'CODCOLIGADA', 'DATAVENCIMENTO'],
        'colunas': {
            'IDLAN':           'NF',
            'CODCOLIGADA':     'Cod_Empresa',
            'DATAEMISSAO':     'Data',
            'DATAVENCIMENTO':  'Vencimento',
            'VALOR':           'Valor',
            'VALORPAGO':       'Valor_Pago',
            'NOMECFO':         'Cliente',
            'CODCFO':          'Cod_Cliente',
            'STATUS':          'Status',
            'HISTORICO':       'Historico',
        },
    },

    # ── TOTVS Datasul ─────────────────────────────────────────
    'TOTVS_DATASUL': {
        'sinais': ['nr-docto', 'nom-clifor', 'dt-emissao'],
        'colunas': {
            'nr-docto':    'NF',
            'dt-emissao':  'Data',
            'dt-vencto':   'Vencimento',
            'vl-docto':    'Valor',
            'nom-clifor':  'Entidade',
            'cod-clifor':  'Cod_Entidade',
            'sit-docto':   'Status',
        },
    },

    # ── Omie ERP ─────────────────────────────────────────────
    'OMIE': {
        'sinais': ['numero_documento', 'nome_cliente', 'valor_documento'],
        'colunas': {
            'numero_documento':    'NF',
            'data_vencimento':     'Vencimento',
            'data_emissao':        'Data',
            'data_lancamento':     'Data_Lancamento',
            'valor_documento':     'Valor',
            'valor_lancamento':    'Valor_Lancamento',
            'nome_cliente':        'Cliente',
            'nome_fornecedor':     'Fornecedor',
            'cnpj_cpf':            'CNPJ_CPF',
            'status_titulo':       'Status',
            'descricao_categoria': 'Categoria',
            'codigo_categoria':    'Cod_Categoria',
            'conta_corrente':      'Conta',
            'tipo_lancamento':     'Tipo',
        },
    },

    # ── Questor ───────────────────────────────────────────────
    'QUESTOR': {
        'sinais': ['DT_LANCTO', 'VL_LANCTO', 'CD_CONTA_DB'],
        'colunas': {
            'DT_LANCTO':    'Data',
            'DS_HISTORICO': 'Historico',
            'VL_LANCTO':    'Valor',
            'CD_CONTA_DB':  'Conta_Debito',
            'CD_CONTA_CR':  'Conta_Credito',
            'CD_CC':        'Centro_Custo',
            'NR_NF':        'NF',
            'DT_EMISSAO':   'Emissao',
            'NM_FORNECEDOR':'Fornecedor',
            'VL_TOTAL':     'Valor_Total',
            'CD_CFOP':      'CFOP',
        },
    },

    # ── SAP Business One ─────────────────────────────────────
    'SAP_B1': {
        'sinais': ['DocNum', 'CardName', 'DocTotal'],
        'colunas': {
            'DocNum':     'NF',
            'DocDate':    'Data',
            'DocDueDate': 'Vencimento',
            'CardCode':   'Cod_Entidade',
            'CardName':   'Entidade',
            'DocTotal':   'Valor',
            'PaidToDate': 'Valor_Pago',
            'DocStatus':  'Status',
            'TransId':    'ID_Lancamento',
            'RefDate':    'Data_Referencia',
            'Account':    'Conta',
            'LineMemo':   'Historico',
            'ProfitCode': 'Centro_Custo',
        },
    },

    # ── Domínio (Thomson Reuters) ─────────────────────────────
    'DOMINIO': {
        'sinais': ['Histórico', 'Débito', 'Crédito'],
        'colunas': {
            'Data':        'Data',
            'Histórico':   'Historico',
            'Débito':      'Conta_Debito',
            'Crédito':     'Conta_Credito',
            'Valor':       'Valor',
            'C. Custo':    'Centro_Custo',
            'Complemento': 'Descricao',
        },
    },

    # ── Sankhya ──────────────────────────────────────────────
    'SANKHYA': {
        'sinais': ['NUMNOTA', 'NOMEPARC', 'VLRNOTA'],
        'colunas': {
            'NUMNOTA':   'NF',
            'DTNEG':     'Data',
            'DTVENC':    'Vencimento',
            'VLRNOTA':   'Valor',
            'VLRPAGO':   'Valor_Pago',
            'NOMEPARC':  'Cliente',
            'CGCPF':     'CNPJ_CPF',
            'CODTIPOPER':'Tipo',
            'STATUSNOTA':'Status',
        },
    },

    # ── Senior Sistemas ───────────────────────────────────────
    'SENIOR': {
        'sinais': ['NumTit', 'NomCli', 'ValTit'],
        'colunas': {
            'NumTit':  'NF',
            'DatEmi':  'Data',
            'DatVen':  'Vencimento',
            'ValTit':  'Valor',
            'ValPag':  'Valor_Pago',
            'NomCli':  'Cliente',
            'CnpCpf':  'CNPJ_CPF',
            'SitTit':  'Status',
            'CodCli':  'Cod_Cliente',
        },
    },

    # ── Cigam ─────────────────────────────────────────────────
    'CIGAM': {
        'sinais': ['NUMERO_TITULO', 'VALOR_TITULO', 'DATA_EMISSAO'],
        'colunas': {
            'NUMERO_TITULO':   'NF',
            'DATA_EMISSAO':    'Data',
            'DATA_VENCIMENTO': 'Vencimento',
            'VALOR_TITULO':    'Valor',
            'VALOR_PAGO':      'Valor_Pago',
            'NOME_CLIENTE':    'Cliente',
            'CNPJ_CPF':        'CNPJ_CPF',
            'SITUACAO':        'Status',
        },
    },

    # ── Alterdata ─────────────────────────────────────────────
    'ALTERDATA': {
        'sinais': ['nr_lancamento', 'vl_lancamento', 'dt_lancamento'],
        'colunas': {
            'nr_lancamento':  'NF',
            'dt_lancamento':  'Data',
            'dt_vencimento':  'Vencimento',
            'vl_lancamento':  'Valor',
            'ds_historico':   'Historico',
            'nm_fornecedor':  'Fornecedor',
            'nm_cliente':     'Cliente',
            'cd_centrocusto': 'Centro_Custo',
        },
    },

    # ── Linx ──────────────────────────────────────────────────
    'LINX': {
        'sinais': ['COD_NF', 'VL_TOTAL', 'NM_CLIENTE'],
        'colunas': {
            'COD_NF':        'NF',
            'DT_EMISSAO':    'Data',
            'DT_VENCIMENTO': 'Vencimento',
            'VL_TOTAL':      'Valor',
            'NM_CLIENTE':    'Cliente',
            'CNPJ_CPF':      'CNPJ_CPF',
            'STATUS':        'Status',
        },
    },

    # ── Mega Sistemas ─────────────────────────────────────────
    'MEGA': {
        'sinais': ['num_doc', 'vl_doc', 'nm_parceiro'],
        'colunas': {
            'num_doc':    'NF',
            'dt_doc':     'Data',
            'dt_vencto':  'Vencimento',
            'vl_doc':     'Valor',
            'vl_pago':    'Valor_Pago',
            'nm_parceiro':'Entidade',
            'cd_parceiro':'Cod_Entidade',
            'sit_titulo': 'Status',
        },
    },

    # ── Nibo ──────────────────────────────────────────────────
    'NIBO': {
        'sinais': ['data_pagamento', 'valor', 'categoria'],
        'colunas': {
            'descricao':      'Historico',
            'data_pagamento': 'Data',
            'data_vencimento':'Vencimento',
            'valor':          'Valor',
            'categoria':      'Categoria',
            'competencia':    'Competencia',
            'status':         'Status',
            'fornecedor':     'Fornecedor',
            'cliente':        'Cliente',
        },
    },

    # ── Granatum ──────────────────────────────────────────────
    'GRANATUM': {
        'sinais': ['data_vencimento', 'valor', 'categoria'],
        'colunas': {
            'descricao':       'Historico',
            'data_vencimento': 'Vencimento',
            'data_pagamento':  'Data',
            'valor':           'Valor',
            'categoria':       'Categoria',
            'status':          'Status',
            'conta':           'Conta',
            'contato':         'Entidade',
        },
    },

    # ── Conta Azul ────────────────────────────────────────────
    'CONTA_AZUL': {
        'sinais': ['Emissão', 'Vencimento', 'Cliente/Fornecedor'],
        'colunas': {
            'Número':              'NF',
            'Emissão':             'Data',
            'Vencimento':          'Vencimento',
            'Valor':               'Valor',
            'Cliente/Fornecedor':  'Entidade',
            'Situação':            'Status',
            'Categoria':           'Categoria',
            'CNPJ/CPF':            'CNPJ_CPF',
        },
    },

    # ── Bling ─────────────────────────────────────────────────
    'BLING': {
        'sinais': ['numero', 'contato', 'situacao', 'cnpjcpf'],
        'colunas': {
            'numero':     'NF',
            'data':       'Data',
            'vencimento': 'Vencimento',
            'valor':      'Valor',
            'contato':    'Entidade',
            'situacao':   'Status',
            'categoria':  'Categoria',
            'cnpjcpf':    'CNPJ_CPF',
        },
    },

    # ── Tiny ERP ──────────────────────────────────────────────
    'TINY': {
        'sinais': ['numero_nota', 'nome_cliente', 'valor_nota'],
        'colunas': {
            'numero_nota':    'NF',
            'data_emissao':   'Data',
            'data_vencimento':'Vencimento',
            'valor_nota':     'Valor',
            'nome_cliente':   'Cliente',
            'cpf_cnpj':       'CNPJ_CPF',
            'situacao':       'Status',
        },
    },

    # ── GestãoClick ──────────────────────────────────────────
    'GESTAO_CLICK': {
        'sinais': ['Código', 'Cliente', 'Vencimento', 'Categoria'],
        'colunas': {
            'Código':     'NF',
            'Data':       'Data',
            'Vencimento': 'Vencimento',
            'Valor':      'Valor',
            'Cliente':    'Cliente',
            'Status':     'Status',
            'Categoria':  'Categoria',
        },
    },

    # ── NFe XML (exportada) ───────────────────────────────────
    'NFE_XML': {
        'sinais': ['nNF', 'dhEmi', 'vNF'],
        'colunas': {
            'nNF':    'NF',
            'dhEmi':  'Data',
            'dVenc':  'Vencimento',
            'vNF':    'Valor',
            'xNome_dest': 'Cliente',
            'xNome_emit': 'Fornecedor',
            'CNPJ_dest':  'CNPJ_CPF',
            'xMun_dest':  'Municipio',
            'cStat':      'Status',
        },
    },
}


# Assinaturas para auto-detecção: mínimo 2 de N colunas devem estar presentes
ASSINATURAS_ERP: Dict[str, list] = {
    erp: data['sinais'] for erp, data in MAPAS_ERP.items()
}


def detectar_erp(df: pd.DataFrame) -> Optional[str]:
    """
    Detecta o ERP de origem pelos nomes das colunas.

    Retorna o nome do ERP (chave de MAPAS_ERP) ou None se não reconhecido.
    Critério: pelo menos 2 colunas-sinal do ERP presentes no DataFrame.
    """
    colunas = set(df.columns)
    melhor_erp: Optional[str] = None
    melhor_score = 0

    for erp, sinais in ASSINATURAS_ERP.items():
        hits = sum(1 for s in sinais if s in colunas)
        if hits >= 2 and hits > melhor_score:
            melhor_score = hits
            melhor_erp = erp

    return melhor_erp


def normalizar_colunas(df: pd.DataFrame, erp: Optional[str] = None) -> pd.DataFrame:
    """
    Renomeia colunas do DataFrame para o padrão do toolkit.

    Se `erp` não for informado, tenta detectar automaticamente.
    Retorna o DataFrame com colunas renomeadas (sem alterar o original).
    """
    if erp is None:
        erp = detectar_erp(df)
    if erp is None or erp not in MAPAS_ERP:
        return df.copy()
    return df.rename(columns=MAPAS_ERP[erp]['colunas'])


__all__ = ['MAPAS_ERP', 'ASSINATURAS_ERP', 'detectar_erp', 'normalizar_colunas']
