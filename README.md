# Planilha Financeira Pro

> Dashboard financeiro 100% no browser + toolkit Python para empresas brasileiras

**Powered by [Luan Guilherme Lourenço](https://github.com/euguilouren)**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green)

**[Abrir dashboard online →](https://euguilouren.github.io/Planilhas/)**

---

## Visão Geral

Arraste qualquer planilha `.xlsx` ou `.csv` e obtenha em segundos:

- **KPIs financeiros**: receitas, despesas, resultado líquido, ticket médio
- **Auditoria**: duplicatas, outliers, campos vazios, inconsistências temporais
- **Aging / Contas a Receber**: faixas de vencimento com gráfico visual
- **DRE automático**: classifica receitas, CMV e despesas (padrão CPC 26)
- **Pareto (curva ABC)**: clientes/fornecedores que geram 80% do resultado
- **Verificação de integridade**: checksum, cross-checks, badges de confiança
- **Detecção automática de ERP**: mapeia colunas de 20 sistemas brasileiros

**ERPs suportados (20):** TOTVS Protheus · TOTVS RM · TOTVS Datasul · Omie · Questor · SAP B1 · Domínio · Sankhya · Senior · Cigam · Alterdata · Linx · Mega · Nibo · Granatum · Conta Azul · Bling · Tiny · GestãoClick · NFe XML

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
├── src/index.html           # Dashboard web — fonte legível (entrada do pipeline)
├── index.html               # Cópia de desenvolvimento para testes locais
├── scripts/
│   └── obfuscar_html.py     # Extrai, obfusca JS e reconstrói HTML para deploy
├── toolkit_financeiro.py    # Biblioteca core Python (12 classes)
├── motor_automatico.py      # Daemon que monitora pasta_entrada/ continuamente
├── rodar.py                 # CLI interativo (gera Excel + briefing)
├── relatorio_html.py        # Gerador de relatórios HTML
├── config.yaml              # Configuração central
├── requirements.txt         # Dependências Python (produção)
├── requirements-dev.txt     # Dependências de desenvolvimento + testes
├── tests/                   # Suite de testes pytest
│   ├── conftest.py
│   ├── test_toolkit_financeiro.py
│   └── test_relatorio_html.py
├── base_conhecimento/
│   ├── __init__.py          # MAPAS_ERP (20 ERPs), detectar_erp(), normalizar_colunas()
│   ├── erp_mapeamentos.md   # Documentação dos 20 mapeamentos ERP
│   └── contabilidade_br.md  # Referência contábil brasileira (CPC 26)
└── .github/workflows/
    ├── ci.yml               # Testes Python 3.10/3.11/3.12 + validações
    └── deploy.yml           # Obfusca JS e publica no gh-pages
```

### Pipeline de Deploy

```
push → main
  └─► deploy.yml
        → python3 scripts/obfuscar_html.py src/index.html dist/index.html
        → peaceiris/actions-gh-pages → branch gh-pages
        → GitHub Pages serve o JS obfuscado em euguilouren.github.io/Planilhas/
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
