# Mapeamentos de ERP — Normalização de Colunas

> 20 sistemas suportados. Detecção automática via `detectar_erp()` em Python
> e `detectarERP()` no dashboard web.

## Como usar

```python
from base_conhecimento import detectar_erp, normalizar_colunas

erp = detectar_erp(df)           # detecta automaticamente
df_norm = normalizar_colunas(df) # aplica mapeamento
```

---

## Campos Universais — Após Normalização

| Campo padrão | Tipo | Descrição |
|---|---|---|
| `NF` | str | Número do documento / NF |
| `Data` | date | Data de emissão / lançamento |
| `Vencimento` | date | Data de vencimento |
| `Valor` | float | Valor principal |
| `Valor_Pago` | float | Valor já pago/baixado |
| `Cliente` | str | Nome do cliente |
| `Fornecedor` | str | Nome do fornecedor |
| `Entidade` | str | Cliente ou fornecedor (genérico) |
| `Cod_Cliente` | str | Código do cliente no ERP |
| `CNPJ_CPF` | str | Documento da entidade |
| `Status` | str | Situação do título |
| `Categoria` | str | Classificação / natureza |
| `Centro_Custo` | str | Centro de custo |
| `Conta` | str | Conta contábil |
| `Historico` | str | Histórico / descrição |

---

## Grupo TOTVS

### TOTVS Protheus (SE1 — Contas a Receber)

Sinais de detecção: `E1_NUM`, `E1_CLIENTE`, `E1_VALOR`

| Coluna ERP | Coluna padrão |
|---|---|
| E1_NUM | NF |
| E1_NOMCLI | Cliente |
| E1_CLIENTE | Cod_Cliente |
| E1_VALOR | Valor |
| E1_SALDO | Saldo |
| E1_VENCTO | Vencimento |
| E1_EMISSAO | Data |
| E1_BAIXA | Data_Baixa |
| E1_SITUACA | Status |
| E1_TIPO | Tipo |
| E1_PREFIXO | Prefixo |

**Situações:** A=Aberto · B=Baixado · V=Vencido · P=Parcial

---

### TOTVS RM

Sinais de detecção: `IDLAN`, `CODCOLIGADA`, `DATAVENCIMENTO`

| Coluna ERP | Coluna padrão |
|---|---|
| IDLAN | NF |
| CODCOLIGADA | Cod_Empresa |
| DATAEMISSAO | Data |
| DATAVENCIMENTO | Vencimento |
| VALOR | Valor |
| VALORPAGO | Valor_Pago |
| NOMECFO | Cliente |
| CODCFO | Cod_Cliente |
| STATUS | Status |
| HISTORICO | Historico |

---

### TOTVS Datasul

Sinais de detecção: `nr-docto`, `nom-clifor`, `dt-emissao`

| Coluna ERP | Coluna padrão |
|---|---|
| nr-docto | NF |
| dt-emissao | Data |
| dt-vencto | Vencimento |
| vl-docto | Valor |
| nom-clifor | Entidade |
| cod-clifor | Cod_Entidade |
| sit-docto | Status |

---

## Grupo Mid-Market BR

### Omie ERP

Sinais de detecção: `numero_documento`, `nome_cliente`, `valor_documento`

| Coluna ERP | Coluna padrão |
|---|---|
| numero_documento | NF |
| data_vencimento | Vencimento |
| data_emissao / data_lancamento | Data |
| valor_documento / valor_lancamento | Valor |
| nome_cliente | Cliente |
| nome_fornecedor | Fornecedor |
| cnpj_cpf | CNPJ_CPF |
| status_titulo | Status |
| descricao_categoria | Categoria |
| codigo_categoria | Cod_Categoria |
| conta_corrente | Conta |
| tipo_lancamento | Tipo |

**Status:** RECEBIDO · ATRASADO · A_RECEBER · CANCELADO

---

### Questor

Sinais de detecção: `DT_LANCTO`, `VL_LANCTO`, `CD_CONTA_DB`

| Coluna ERP | Coluna padrão |
|---|---|
| DT_LANCTO | Data |
| DS_HISTORICO | Historico |
| VL_LANCTO / VL_TOTAL | Valor |
| CD_CONTA_DB | Conta_Debito |
| CD_CONTA_CR | Conta_Credito |
| CD_CC | Centro_Custo |
| NR_NF | NF |
| DT_EMISSAO | Emissao |
| NM_FORNECEDOR | Fornecedor |
| CD_CFOP | CFOP |

---

### Domínio (Thomson Reuters)

Sinais de detecção: `Histórico`, `Débito`, `Crédito`

| Coluna ERP | Coluna padrão |
|---|---|
| Data | Data |
| Histórico | Historico |
| Débito | Conta_Debito |
| Crédito | Conta_Credito |
| Valor | Valor |
| C. Custo | Centro_Custo |
| Complemento | Descricao |

---

### Sankhya

Sinais de detecção: `NUMNOTA`, `NOMEPARC`, `VLRNOTA`

| Coluna ERP | Coluna padrão |
|---|---|
| NUMNOTA | NF |
| DTNEG | Data |
| DTVENC | Vencimento |
| VLRNOTA | Valor |
| VLRPAGO | Valor_Pago |
| NOMEPARC | Cliente |
| CGCPF | CNPJ_CPF |
| CODTIPOPER | Tipo |
| STATUSNOTA | Status |

---

### Senior Sistemas

Sinais de detecção: `NumTit`, `NomCli`, `ValTit`

| Coluna ERP | Coluna padrão |
|---|---|
| NumTit | NF |
| DatEmi | Data |
| DatVen | Vencimento |
| ValTit | Valor |
| ValPag | Valor_Pago |
| NomCli | Cliente |
| CnpCpf | CNPJ_CPF |
| SitTit | Status |
| CodCli | Cod_Cliente |

---

### Cigam

Sinais de detecção: `NUMERO_TITULO`, `VALOR_TITULO`, `DATA_EMISSAO`

| Coluna ERP | Coluna padrão |
|---|---|
| NUMERO_TITULO | NF |
| DATA_EMISSAO | Data |
| DATA_VENCIMENTO | Vencimento |
| VALOR_TITULO | Valor |
| VALOR_PAGO | Valor_Pago |
| NOME_CLIENTE | Cliente |
| CNPJ_CPF | CNPJ_CPF |
| SITUACAO | Status |

---

### Alterdata

Sinais de detecção: `nr_lancamento`, `vl_lancamento`, `dt_lancamento`

| Coluna ERP | Coluna padrão |
|---|---|
| nr_lancamento | NF |
| dt_lancamento | Data |
| dt_vencimento | Vencimento |
| vl_lancamento | Valor |
| ds_historico | Historico |
| nm_fornecedor | Fornecedor |
| nm_cliente | Cliente |
| cd_centrocusto | Centro_Custo |

---

### Linx

Sinais de detecção: `COD_NF`, `VL_TOTAL`, `NM_CLIENTE`

| Coluna ERP | Coluna padrão |
|---|---|
| COD_NF | NF |
| DT_EMISSAO | Data |
| DT_VENCIMENTO | Vencimento |
| VL_TOTAL | Valor |
| NM_CLIENTE | Cliente |
| CNPJ_CPF | CNPJ_CPF |
| STATUS | Status |

---

### Mega Sistemas

Sinais de detecção: `num_doc`, `vl_doc`, `nm_parceiro`

| Coluna ERP | Coluna padrão |
|---|---|
| num_doc | NF |
| dt_doc | Data |
| dt_vencto | Vencimento |
| vl_doc | Valor |
| vl_pago | Valor_Pago |
| nm_parceiro | Entidade |
| cd_parceiro | Cod_Entidade |
| sit_titulo | Status |

---

## Grupo SAP

### SAP Business One

Sinais de detecção: `DocNum`, `CardName`, `DocTotal`

| Coluna ERP | Coluna padrão |
|---|---|
| DocNum | NF |
| DocDate | Data |
| DocDueDate | Vencimento |
| CardCode | Cod_Entidade |
| CardName | Entidade |
| DocTotal | Valor |
| PaidToDate | Valor_Pago |
| DocStatus | Status |
| TransId | ID_Lancamento |
| Account | Conta |
| LineMemo | Historico |
| ProfitCode | Centro_Custo |

**DocStatus:** O=Open · C=Closed

---

## Grupo Cloud / PME

### Nibo

Sinais de detecção: `data_pagamento`, `valor`, `categoria`

| Coluna ERP | Coluna padrão |
|---|---|
| descricao | Historico |
| data_pagamento | Data |
| data_vencimento | Vencimento |
| valor | Valor |
| categoria | Categoria |
| competencia | Competencia |
| status | Status |
| fornecedor | Fornecedor |
| cliente | Cliente |

---

### Granatum

Sinais de detecção: `data_vencimento`, `valor`, `categoria`

| Coluna ERP | Coluna padrão |
|---|---|
| descricao | Historico |
| data_vencimento | Vencimento |
| data_pagamento | Data |
| valor | Valor |
| categoria | Categoria |
| status | Status |
| conta | Conta |
| contato | Entidade |

---

### Conta Azul

Sinais de detecção: `Emissão`, `Vencimento`, `Cliente/Fornecedor`

| Coluna ERP | Coluna padrão |
|---|---|
| Número | NF |
| Emissão | Data |
| Vencimento | Vencimento |
| Valor | Valor |
| Cliente/Fornecedor | Entidade |
| Situação | Status |
| Categoria | Categoria |
| CNPJ/CPF | CNPJ_CPF |

---

### Bling

Sinais de detecção: `numero`, `contato`, `situacao`

| Coluna ERP | Coluna padrão |
|---|---|
| numero | NF |
| data | Data |
| vencimento | Vencimento |
| valor | Valor |
| contato | Entidade |
| situacao | Status |
| categoria | Categoria |
| cnpjcpf | CNPJ_CPF |

---

### Tiny ERP

Sinais de detecção: `numero_nota`, `nome_cliente`, `valor_nota`

| Coluna ERP | Coluna padrão |
|---|---|
| numero_nota | NF |
| data_emissao | Data |
| data_vencimento | Vencimento |
| valor_nota | Valor |
| nome_cliente | Cliente |
| cpf_cnpj | CNPJ_CPF |
| situacao | Status |

---

### GestãoClick

Sinais de detecção: `Código`, `Cliente`, `Vencimento`

| Coluna ERP | Coluna padrão |
|---|---|
| Código | NF |
| Data | Data |
| Vencimento | Vencimento |
| Valor | Valor |
| Cliente | Cliente |
| Status | Status |
| Categoria | Categoria |

---

## Grupo Fiscal

### NFe XML (exportada)

Sinais de detecção: `nNF`, `dhEmi`, `vNF`

| Coluna ERP | Coluna padrão |
|---|---|
| nNF | NF |
| dhEmi | Data |
| dVenc | Vencimento |
| vNF | Valor |
| xNome_dest | Cliente |
| xNome_emit | Fornecedor |
| CNPJ_dest | CNPJ_CPF |
| xMun_dest | Municipio |
| cStat | Status |
