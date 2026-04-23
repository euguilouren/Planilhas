"""
Pacote de conhecimento de domínio — mapeamentos de ERPs e contabilidade BR.
"""

MAPAS_ERP = {
    'TOTVS': {
        'E1_NUM':     'NF',
        'E1_CLIENTE': 'Cod_Cliente',
        'E1_NOMCLI':  'Cliente',
        'E1_VALOR':   'Valor',
        'E1_VENCTO':  'Vencimento',
        'E1_EMISSAO': 'Data',
        'E1_SITUACA': 'Status',
        'E1_SALDO':   'Saldo',
    },
    'OMIE': {
        'numero_documento':    'NF',
        'data_vencimento':     'Vencimento',
        'data_emissao':        'Data',
        'valor_documento':     'Valor',
        'nome_cliente':        'Cliente',
        'cnpj_cpf':            'CNPJ_CPF',
        'status_titulo':       'Status',
        'descricao_categoria': 'Categoria',
    },
    'QUESTOR': {
        'DT_LANCTO':    'Data',
        'DS_HISTORICO': 'Historico',
        'VL_LANCTO':    'Valor',
        'CD_CONTA_DB':  'Conta_Debito',
        'NR_NF':        'NF',
        'NM_FORNECEDOR':'Fornecedor',
    },
    'SAP_B1': {
        'DocNum':     'NF',
        'DocDate':    'Data',
        'DocDueDate': 'Vencimento',
        'CardName':   'Entidade',
        'DocTotal':   'Valor',
        'DocStatus':  'Status',
    },
}
