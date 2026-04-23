# 📊 Toolkit Financeiro

> Análise autônoma de planilhas financeiras para empresas brasileiras

**Powered by [Luan Guilherme Lourenço](https://github.com/euguilouren)**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green)

---

## Visão Geral

O Toolkit Financeiro automatiza a análise de planilhas Excel e CSV, entregando:

- **Auditoria**: detecção de duplicatas, outliers, campos vazios e inconsistências temporais
- **Aging / Contas a Receber**: faixas de vencimento, PCLD sugerida por bucket
- **DRE automático**: classifica receitas, CMV e despesas conforme padrões brasileiros (CPC 26)
- **Análise Pareto (curva ABC)**: identifica os clientes/fornecedores que geram 80% do resultado
- **Conciliação**: reconciliação exata e fuzzy entre planilhas
- **Relatório HTML e Excel**: formatados, coloridos e prontos para apresentação

Suporte a ERPs: **TOTVS · Omie · Questor · SAP B1 · Domínio Sistemas**

---

## Modos de Uso

| Modo | Arquivo | Descrição |
|------|---------|-----------|
| Dashboard web | `index.html` | Abre no navegador, sem servidor, sem instalar Python |
| CLI interativo | `rodar.py` | Processa um arquivo e gera Excel + briefing |
| Monitor autônomo | `motor_automatico.py` | Daemon que monitora uma pasta continuamente |
| Relatório HTML | `relatorio_html.py` | Biblioteca usada pelo daemon |

---

## Instalação Rápida

```bash
# 1. Clone o repositório
git clone https://github.com/euguilouren/planilhas
cd planilhas

# 2. Instale as dependências
pip install -r requirements.txt
```

**No Windows** use o instalador incluso:
```
instalar.bat   # instala dependências
abrir.bat      # abre o dashboard no navegador
```

---

## Uso

### Opção A — Dashboard no Navegador (sem Python)

Abra `index.html` diretamente no Chrome, Edge ou Firefox.  
Arraste e solte qualquer planilha `.xlsx` ou `.csv` para analisar instantaneamente.

### Opção B — CLI (um arquivo)

```bash
# Edite ARQUIVO_ENTRADA no início do script
python rodar.py
```

Gera `resultado.xlsx` e `briefing.txt` na mesma pasta.

### Opção C — Monitor Autônomo

```bash
# Configure config.yaml (veja seção abaixo)
python motor_automatico.py              # monitora pasta_entrada/ continuamente
python motor_automatico.py --once       # processa uma vez e sai
python motor_automatico.py --arquivo minha.xlsx  # arquivo específico
```

---

## Configuração (`config.yaml`)

| Chave | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `pastas.entrada` | string | `pasta_entrada` | Pasta monitorada pelo daemon |
| `pastas.saida` | string | `pasta_saida` | Onde os relatórios são gerados |
| `colunas.valor` | string | `Valor` | Nome da coluna de valores monetários |
| `colunas.categoria` | string | `Categoria` | Nome da coluna de categorias DRE |
| `colunas.data` | string | `Data` | Coluna de data de emissão |
| `colunas.vencimento` | string | `Vencimento` | Coluna de data de vencimento |
| `colunas.chave` | string | `NF` | Chave única (nota fiscal, ID) |
| `colunas.entidade` | string | `Cliente` | Cliente ou fornecedor |
| `auditoria.outlier_desvios` | float | `3.0` | Desvios padrão para detectar outlier |
| `aging.faixa_atencao` | int | `30` | Dias de atraso → ATENÇÃO |
| `aging.faixa_critica` | int | `90` | Dias de atraso → CRÍTICO |
| `indicadores.liquidez_corrente_min` | float | `1.0` | Mínimo de liquidez corrente saudável |
| `indicadores.margem_liquida_min` | float | `5.0` | Margem líquida mínima (%) |
| `analise_comercial.pareto_corte` | float | `0.80` | Corte da curva ABC (padrão 80%) |
| `email.ativo` | bool | `false` | Habilita alertas por e-mail |
| `relatorio.empresa` | string | `Minha Empresa` | Nome exibido nos relatórios |

---

## Estrutura do Projeto

```
Planilhas/
├── toolkit_financeiro.py    # Biblioteca core (12 classes, ~1600 linhas)
├── motor_automatico.py      # Daemon de monitoramento autônomo
├── rodar.py                 # CLI interativo
├── relatorio_html.py        # Gerador de relatórios HTML
├── index.html               # Dashboard web (zero dependências)
├── config.yaml              # Configuração central
├── requirements.txt         # Dependências Python (produção)
├── requirements-dev.txt     # Dependências de desenvolvimento + testes
├── tests/                   # Suite de testes pytest (60 testes)
│   ├── conftest.py
│   ├── test_toolkit_financeiro.py
│   └── test_relatorio_html.py
├── base_conhecimento/
│   ├── erp_mapeamentos.md   # Mapeamentos de campos TOTVS, Omie, SAP B1...
│   └── contabilidade_br.md  # Referência contábil brasileira (CPC 26)
├── instalar.sh / instalar.bat
└── abrir.sh / abrir.bat
```

### Módulos do `toolkit_financeiro.py`

| Classe | Responsabilidade |
|--------|-----------------|
| `Leitor` | Leitura de Excel/CSV com diagnóstico completo |
| `Auditor` | Duplicatas, outliers, campos vazios, inconsistências |
| `Conciliador` | Reconciliação exata e fuzzy entre planilhas |
| `AnalistaFinanceiro` | Aging, DRE, indicadores de saúde (LC, LS, ROE...) |
| `AnalistaComercial` | Pareto, ticket médio, realizado vs meta |
| `PrestadorContas` | Balanço, comparativo de períodos |
| `MontadorPlanilha` | Excel profissional com formatação e totais |
| `Verificador` | Integridade pós-processamento (contagem, soma) |
| `Util` | Normalização, CNPJ/CPF, conversão moeda BR, similaridade |
| `PipelineFinanceiro` | Orquestração encadeada de análises |
| `Estilos` | Constantes de formatação Excel |
| `Status` | Enumeração de status e severidade |

---

## Desenvolvimento e Testes

```bash
# Instalar dependências de dev
pip install -r requirements-dev.txt

# Rodar todos os testes
pytest tests/ -v

# Testes com relatório de cobertura
pytest tests/ -v --cov=toolkit_financeiro --cov=relatorio_html --cov-report=term-missing
```

60 testes cobrindo: `Leitor`, `Auditor`, `AnalistaFinanceiro`, `AnalistaComercial`,
`Util`, `Verificador`, `validar_config` e `GeradorHTML`.

---

## Licença

MIT © Luan Guilherme Lourenço
