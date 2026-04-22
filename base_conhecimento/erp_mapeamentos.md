# Mapeamentos de ERP — Normalização de Colunas

## Como usar
Ao receber uma planilha exportada de um ERP, identifique o sistema
e aplique o mapeamento abaixo para normalizar os nomes de colunas
antes de passar para o toolkit:

```python
df = df.rename(columns=MAPA_ERP['omie'])  # exemplo
```

---

## TOTVS Protheus

```python
MAPA_TOTVS = {
    # Financeiro / Contas a Receber (SE1)
    'E1_NUM'    : 'NF',
    'E1_PREFIXO': 'Prefixo',
    'E1_TIPO'   : 'Tipo_Titulo',
    'E1_CLIENTE': 'Cod_Cliente',
    'E1_LOJA'   : 'Loja_Cliente',
    'E1_NOMCLI' : 'Cliente',
    'E1_VALOR'  : 'Valor',
    'E1_SALDO'  : 'Saldo',
    'E1_VENCTO' : 'Vencimento',
    'E1_EMISSAO': 'Emissao',
    'E1_BAIXA'  : 'Data_Baixa',
    'E1_SITUACA': 'Situacao',
    # Contabilidade (CT2)
    'CT2_DATA'  : 'Data',
    'CT2_DC'    : 'Debito_Credito',
    'CT2_VALOR' : 'Valor',
    'CT2_HIST'  : 'Historico',
    'CT2_CTA'   : 'Conta',
    'CT2_CLVL'  : 'Centro_Custo',
    # Estoque/NF (SD2/SF2)
    'D2_DOC'    : 'NF',
    'D2_EMISSAO': 'Emissao',
    'D2_FORNECE': 'Cod_Fornecedor',
    'D2_NFORNEC': 'Fornecedor',
    'D2_TOTAL'  : 'Valor',
    'D2_CF'     : 'CFOP',
}
```

**Situações comuns do Protheus:**
| Código | Descrição |
|--------|-----------|
| A | Em aberto |
| B | Baixado |
| V | Vencido |
| P | Parcialmente pago |

---

## Omie ERP

```python
MAPA_OMIE = {
    # Contas a Receber
    'numero_documento'      : 'NF',
    'data_vencimento'       : 'Vencimento',
    'data_emissao'          : 'Emissao',
    'valor_documento'       : 'Valor',
    'valor_recebido'        : 'Valor_Recebido',
    'nome_cliente'          : 'Cliente',
    'cnpj_cpf'              : 'CNPJ_CPF',
    'status_titulo'         : 'Status',
    'categoria'             : 'Categoria',
    'conta_corrente'        : 'Conta',
    # Contas a Pagar
    'nome_fornecedor'       : 'Fornecedor',
    'valor_pagar'           : 'Valor',
    'data_pagamento'        : 'Data_Pagamento',
    # DRE / Financeiro
    'descricao'             : 'Descricao',
    'valor_lancamento'      : 'Valor',
    'tipo_lancamento'       : 'Tipo',   # Receita / Despesa
    'data_lancamento'       : 'Data',
    'codigo_categoria'      : 'Cod_Categoria',
    'descricao_categoria'   : 'Categoria',
}
```

**Status de títulos Omie:**
| Status | Descrição |
|--------|-----------|
| RECEBIDO | Baixado/pago |
| ATRASADO | Vencido sem baixa |
| A_RECEBER | Em aberto dentro do prazo |
| CANCELADO | Cancelado |

---

## Domínio Sistemas (Thomson Reuters)

```python
MAPA_DOMINIO = {
    # Lançamentos Contábeis
    'Data'              : 'Data',
    'Histórico'         : 'Historico',
    'Débito'            : 'Conta_Debito',
    'Crédito'           : 'Conta_Credito',
    'Valor'             : 'Valor',
    'C. Custo'          : 'Centro_Custo',
    'Complemento'       : 'Descricao',
    # Folha de Pagamento
    'Funcionário'       : 'Funcionario',
    'CPF'               : 'CPF',
    'Admissão'          : 'Data_Admissao',
    'Sal. Base'         : 'Salario_Base',
    'Proventos'         : 'Proventos',
    'Descontos'         : 'Descontos',
    'Líquido'           : 'Salario_Liquido',
    'INSS'              : 'INSS',
    'FGTS'              : 'FGTS',
    'IRRF'              : 'IRRF',
}
```

---

## Questor Sistemas

```python
MAPA_QUESTOR = {
    # Contabilidade
    'DT_LANCTO'     : 'Data',
    'DS_HISTORICO'  : 'Historico',
    'VL_LANCTO'     : 'Valor',
    'CD_CONTA_DB'   : 'Conta_Debito',
    'CD_CONTA_CR'   : 'Conta_Credito',
    'CD_CC'         : 'Centro_Custo',
    # Fiscal
    'NR_NF'         : 'NF',
    'DT_EMISSAO'    : 'Emissao',
    'NM_FORNECEDOR' : 'Fornecedor',
    'VL_TOTAL'      : 'Valor',
    'VL_ICMS'       : 'ICMS',
    'VL_PIS'        : 'PIS',
    'VL_COFINS'     : 'COFINS',
    'CD_CFOP'       : 'CFOP',
}
```

---

## SAP Business One (B1)

```python
MAPA_SAP_B1 = {
    # Faturas (OINV / OPCH)
    'DocNum'    : 'NF',
    'DocDate'   : 'Emissao',
    'DocDueDate': 'Vencimento',
    'CardCode'  : 'Cod_Entidade',
    'CardName'  : 'Entidade',
    'DocTotal'  : 'Valor',
    'PaidToDate': 'Valor_Pago',
    'DocStatus' : 'Status',   # O=Open, C=Closed
    # Contabilidade (JDT1)
    'TransId'   : 'ID_Lancamento',
    'RefDate'   : 'Data',
    'Account'   : 'Conta',
    'Debit'     : 'Debito',
    'Credit'    : 'Credito',
    'LineMemo'  : 'Historico',
    'ProfitCode': 'Centro_Custo',
}
```

---

## Função de auto-detecção de ERP

Adicione ao toolkit para detectar automaticamente:

```python
def detectar_erp(df: pd.DataFrame) -> str:
    """Detecta o ERP de origem baseado nos nomes das colunas."""
    cols = set(df.columns.str.upper())
    sinais = {
        'TOTVS'  : {'E1_NUM', 'E1_CLIENTE', 'CT2_DATA', 'D2_DOC'},
        'OMIE'   : {'NUMERO_DOCUMENTO', 'NOME_CLIENTE', 'CODIGO_CATEGORIA'},
        'DOMINIO': {'HISTÓRICO', 'SAL. BASE', 'PROVENTOS', 'DESCONTOS'},
        'QUESTOR': {'DT_LANCTO', 'VL_LANCTO', 'CD_CONTA_DB'},
        'SAP_B1' : {'DOCNUM', 'CARDCODE', 'CARDNAME', 'DOCTOTAL'},
    }
    for erp, campos in sinais.items():
        if len(campos & cols) >= 2:
            return erp
    return 'DESCONHECIDO'
```

---

## Campos Universais — Após Normalização

Após aplicar qualquer mapeamento, o DataFrame deve ter estas colunas padronizadas:

| Campo padrão | Tipo | Descrição |
|---|---|---|
| `NF` | str | Número do documento/NF |
| `Emissao` | date | Data de emissão |
| `Vencimento` | date | Data de vencimento |
| `Data` | date | Data do lançamento |
| `Valor` | float | Valor principal |
| `Cliente` ou `Fornecedor` | str | Nome da entidade |
| `CNPJ_CPF` | str (14 dígitos) | Documento da entidade |
| `Categoria` | str | Classificação/natureza |
| `Status` | str | Situação do título |
| `Centro_Custo` | str | Centro de custo |
| `Conta` | str | Conta contábil |
