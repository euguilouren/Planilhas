# CLAUDE.md — Planilha Financeira Pro

> Guia de arquitetura para refinamentos. Leia antes de qualquer edição.

## Arquitetura em uma linha

`index.html` é o produto inteiro (~860 linhas). Python é backend opcional não usado no GitHub Pages.
Análise 100% client-side: SheetJS lê XLSX/CSV, Chart.js renderiza gráfico de aging, tudo no browser.

---

## Mapa de Seções do index.html

| Linhas | Bloco | Responsabilidade |
|--------|-------|-----------------|
| 1–14 | `<head>` + CDNs | SheetJS 0.20.3, Chart.js 4.4.0 via CDN |
| 15–524 | `<script>` analise.js | Módulos **puros de cálculo** — sem DOM |
| 20–36 | `PADROES_COLUNAS` + `detectarColunas()` | 7 regex genéricas que mapeiam colunas por nome |
| 38–79 | Funções utilitárias | `toNum()`, `toDate()`, `fmtBRL()`, `fmtNum()`, `fmtData()` |
| 83–181 | `auditoria()` | Duplicatas, campos vazios, outliers, datas futuras |
| 187–222 | `calcularAging()` | Aging de recebíveis em 5 faixas |
| 227–247 | `calcularPareto()` | Top 15 entidades com % acumulado |
| 252–301 | `MAPA_DRE` + `construirDRE()` | Monta DRE por regex de categorias |
| 305–465 | `calcularKPIs()` + `calcularFluxoPeriodo()` | KPIs financeiros + fluxo por período |
| 466–524 | `<style>` fim analise.js | (fechamento do primeiro script) |
| 466–524 | `<style>` | CSS completo — variáveis em `:root`, layout, responsivo |
| 525–849 | `<script>` app.js | Estado global, eventos, funções render |
| 529–534 | Estado global | `_dadosOriginais`, `_dadosFiltrados`, `_headers`, `_cols`, `_nomeArquivo`, `_chartAging` |
| 539–549 | Drag & Drop | Eventos `dragover`, `dragleave`, `drop`, `change` no `#file-input` |
| 554–590 | `carregarArquivo()` | FileReader → SheetJS → `detectarColunas()` → `mostrarConfigColunas()` |
| 595–621 | `mostrarConfigColunas()` + `lerColsSelecionadas()` | Renderiza 6 selects de mapeamento de colunas |
| 625–665 | `executarAnalise()` | Orquestra todos os módulos + chama todos os render |
| 670–687 | `renderKPIs()` | Renderiza cards KPI |
| 692–716 | `renderAuditoria()` | Tabela de problemas com badges |
| 720–760 | `renderAging()` | Barras de aging + Chart.js |
| 765–782 | `renderDRE()` | Tabela DRE com cores por tipo |
| 786–803 | `renderPareto()` | Tabela Pareto com badge Classe A |
| 807–827 | `renderTabela()` + `filtrarTabela()` | Tabela de dados brutos com busca |
| 832–848 | Utilitários do app | `mostrarLoader()`, `exportarJSON()` |
| 851–855 | Footer | Branding "Powered by Luan Guilherme Lourenço" |

---

## Variáveis de Estado Global (app.js)

```js
let _dadosOriginais = [];  // array de objetos — nunca modificar diretamente
let _dadosFiltrados = [];  // usado apenas pela busca
let _headers        = [];  // array de strings: cabeçalhos originais do arquivo
let _cols           = {};  // { valor, data, vencimento, categoria, entidade, chave }
let _nomeArquivo    = '';  // nome do arquivo carregado
let _chartAging     = null; // instância Chart.js — SEMPRE destruir antes de recriar
```

---

## Fluxo de Dados

```
arquivo → carregarArquivo()
  → SheetJS → _headers + _dadosOriginais
  → detectarColunas(_headers) → sugestão automática
  → mostrarConfigColunas(_headers, cols) → 6 <select>
  → [usuário confirma]
  → executarAnalise()
      → lerColsSelecionadas() → _cols
      → calcularKPIs / auditoria / calcularAging / construirDRE / calcularPareto
      → renderKPIs / renderAuditoria / renderAging / renderDRE / renderPareto / renderTabela
```

---

## Variáveis CSS (`:root`)

```css
--navy:    #1F4E79   /* cor primária — header, botões, thead */
--gold:    #C9A84C   /* acento — hover, badges Classe A */
--bg:      #F4F6FA   /* fundo geral */
--surface: #FFFFFF   /* cards */
--border:  #E2E8F0   /* bordas */
--text:    #1A1A2E   /* texto principal */
--text-2:  #64748B   /* texto secundário */
--success: #2e7d32   /* verde */
--danger:  #C00000   /* vermelho */
--radius:  8px       /* border-radius padrão (cards) */
--radius-sm: 6px     /* border-radius menor */
```

Breakpoints: `900px` (KPIs 3 cols, grid muda), `600px` (mobile — KPIs 2 cols, toolbar).

---

## Convenções de Código

- Funções em `analise.js` (linhas 15–524): recebem dados como parâmetros, **nunca tocam o DOM**
- Funções `render*()` em `app.js`: **nunca calculam** — só renderizam innerHTML
- IDs HTML: `kebab-case` (ex: `card-aging`, `tbody-dados`)
- IDs de selects: `sel-{tipo}` (ex: `sel-valor`, `sel-data`)
- Prefixo `_` para variáveis de estado global
- Nenhum `console.log` em produção — o obfuscador inclui tudo

---

## Como Adicionar um Novo ERP

### 1. JavaScript (`index.html` — após `PADROES_COLUNAS`)

Adicionar ao objeto `MAPAS_ERP_JS` (a criar na etapa 4):
```js
NOME_ERP: {
  sinais: ['ColunaTipica1', 'ColunaTipica2', 'ColunaTipica3'],
  mapa: {
    'ColunaTipica1': 'NF',        // coluna-ERP : coluna-padrão
    'ColunaTipica2': 'Valor',
    'ColunaTipica3': 'Cliente',
    'ColunaTipica4': 'Data',
    'ColunaTipica5': 'Vencimento',
  }
}
```

Adicionar `<option value="NOME_ERP">Nome Legível</option>` no `<select id="sel-erp-sistema">`.

### 2. Python (`base_conhecimento/__init__.py`)

Adicionar em `MAPAS_ERP`:
```python
'NOME_ERP': {
    'sinais': ['ColunaTipica1', 'ColunaTipica2'],
    'colunas': {
        'valor': 'ColunaTipica2',
        'data': 'ColunaTipica4',
        'chave': 'ColunaTipica1',
        'entidade': 'ColunaTipica3',
    }
}
```

Adicionar em `ASSINATURAS_ERP`: `'NOME_ERP': ['ColunaTipica1', 'ColunaTipica2', 'ColunaTipica3']`

---

## Seções que NÃO Devem Ser Modificadas

| O que | Por quê |
|-------|---------|
| URLs das CDNs (SheetJS, Chart.js) | Versões fixadas — mudança quebra compatibilidade |
| Nomes das 6 chaves de `_cols` (`valor`, `data`, `vencimento`, `categoria`, `entidade`, `chave`) | Usadas em todas as funções de análise |
| `MAPA_DRE` (array de `{linha, termos}`) | Qualquer mudança altera o DRE para todos os usuários |
| `_chartAging.destroy()` antes de `new Chart()` | Sem isso, múltiplos canvas se acumulam na memória |
| `mostrarLoader(true/false)` nos pontos existentes | Remove feedback visual de carregamento |

---

## Pontos de Extensão

| O que adicionar | Onde |
|----------------|------|
| Novo card de análise | Após `</section>` do card de Pareto (~linha 520 HTML), antes do `<section id="dados">` |
| Nova função de cálculo | Final do bloco `analise.js` (antes da linha 524), sem DOM |
| Novo tipo de gráfico | Copiar padrão de `renderAging()` — destruir instância anterior |
| Novo campo de mapeamento | Adicionar chave em `_cols`, label em `mostrarConfigColunas()`, uso em `executarAnalise()` |
| Novo KPI | Retornar do `calcularKPIs()` e renderizar em `renderKPIs()` |

---

## ERPs Suportados

Arquivo: `base_conhecimento/__init__.py` → `MAPAS_ERP`

| Grupo | ERPs |
|-------|------|
| TOTVS | TOTVS (Protheus), TOTVS_RM, TOTVS_DATASUL |
| Mid-market BR | OMIE, QUESTOR, DOMINIO, SANKHYA, SENIOR, CIGAM, ALTERDATA, LINX, MEGA |
| SAP | SAP_B1 |
| Cloud/SMB | CONTA_AZUL, BLING, TINY, NIBO, GRANATUM, GESTAO_CLICK |
| Fiscal | NFE_XML |

---

## Pipeline de Deploy

```
main branch (código legível em src/index.html)
  └─► push → .github/workflows/deploy.yml
        → npm run build (scripts/build.js)
            → javascript-obfuscator (domain-lock: euguilouren.github.io)
            → dist/index.html (ofuscado)
        → peaceiris/actions-gh-pages → branch gh-pages
        → GitHub Pages serve gh-pages
```

`dist/` está no `.gitignore` — nunca comitar manualmente.
`index.html` na raiz é a cópia de desenvolvimento (legível, para `file://` local).

---

## CI/CD

Arquivo: `.github/workflows/ci.yml`

| Job | O que faz |
|-----|-----------|
| `test` | pytest em Python 3.10/3.11/3.12 |
| `validate-html` | Verifica `<!DOCTYPE html>`, "Luan Guilherme", "Planilha Financeira Pro" |
| `security-audit` | pip-audit nas dependências Python |
| `validate-config` | Estrutura do config.yaml |
