# CLAUDE.md — FluxoPRO

> Guia de arquitetura para refinamentos. Leia antes de qualquer edição.

## Arquitetura em uma linha

`index.html` é o produto inteiro (~3676 linhas, monolítico). Python é backend opcional não usado no GitHub Pages.
Análise 100% client-side: SheetJS lê XLSX/CSV (+ OFX nativo via `parseOFX`), Chart.js renderiza aging/fluxo/comparativo, Service Worker (`sw.js`) entrega PWA offline, CSP restringe execução. Briefing IA via Claude API é opcional — chave fica em `sessionStorage`, nunca persistida.

---

## Mapa de Seções do index.html

| Linhas | Bloco | Responsabilidade |
|--------|-------|-----------------|
| 3–52 | `<head>` + CDNs + CSP | CSP meta (linha 6), SheetJS 0.20.3, Chart.js 4.4.0, JSON-LD schema.org |
| 53–1101 | `<script>` analise.js | Módulos **puros de cálculo** — sem DOM, sem `_` globais |
| 64–82 | `PADROES_COLUNAS` + `detectarColunas()` | Regex genéricas (valor, data, vencimento, entidade, chave, categoria, tipo) |
| 86–130 | `MAPAS_ERP_JS` + `NOMES_ERP` + `detectarERP()` | 20 ERPs com `sinais`/`mapa` — aplicado em `lerColsSelecionadas()` |
| 132–281 | `calcularIntegridade()` | Verificação cruzada (soma, contagens, KPIs vs. amostra) |
| 283–387 | `auditoria()` | Duplicatas, campos vazios, outliers, datas futuras |
| 389–429 | `calcularAging()` | Aging de recebíveis em 5 faixas |
| 431–469 | `calcularPareto()` | Top N entidades com % acumulado |
| 462 + 471–534 | `MAPA_DRE` + `construirDRE()` | Monta DRE por regex de categorias |
| 536–619 | `calcularKPIs()` + `calcularFluxoPeriodo()` | KPIs financeiros + fluxo por período |
| 621–686 | `calcularProjecao()` + `calcularSazonalidade()` | Tendência linear + padrões mensais/semanais |
| 688–782 | `renderFluxoPeriodo()` | Render do fluxo (vive em analise.js por histórico) |
| 784–976 | `calcularAntiFraude()` | 12+ regras: duplicatas, round-numbers, gaps, Benford |
| 978–1019 | `calcularScoreFinanceiro()` | Score 0–100 ponderado (KPIs + aging + Pareto + auditoria) |
| 1021–1041 | `calcularKPIsComparativo()` | Delta de KPIs entre 2 datasets |
| 1043–1101 | `parseOFX()` + `_decodeOFXBuffer()` | Parser nativo de extratos OFX |
| 1102–1589 | `<style>` | CSS completo — `:root`, layout, responsivo, dark mode (`[data-theme="dark"]` na linha 1122) |
| 1591–1857 | `<body>` HTML | Header, upload, cards de análise (`#card-*`), painel comparativo, briefing IA, onboarding |
| 1859–3676 | `<script>` app.js | Estado global, eventos, funções render, integração Claude |
| 1866–1893 | Estado global | Ver tabela abaixo |
| 2047–2201 | `carregarArquivo()` | FileReader → SheetJS/OFX → `detectarColunas()` → `detectarERP()` → `mostrarConfigColunas()` |
| 2203–2268 | `carregarArquivoComparativo()` | Mesmo fluxo p/ segundo dataset |
| 2270–2351 | `mostrarConfigColunas()` + `lerColsSelecionadas()` | Selects de mapeamento + aplicação do ERP detectado |
| 2353–2462 | `executarAnalise()` | Orquestra módulos + chama todos os render (async — usa await em IA) |
| 2464–2510 | `renderKPIs()` | Cards KPI |
| 2512–2599 | `renderScoreFinanceiro()` | Score 0–100 com componentes |
| 2601–2651 | `renderVerificacao()` | Painel de integridade |
| 2653–2704 | `renderAuditoria()` | Tabela de problemas com badges |
| 2706–2764 | `renderAging()` | Barras + Chart.js (destruir `_chartAging` antes) |
| 2766–2809 | `renderDRE()` | Tabela DRE com cores por tipo |
| 2811–2840 | `renderPareto()` | Tabela Pareto com badge Classe A |
| 2842–2925 | `renderComparativo()` | Tabela + Chart.js (`_chartComparativo`) |
| 2927–3007 | `renderAntiFraude()` | Alertas de fraude agrupados |
| 3009–3364 | `renderTabela()` + `filtrarTabela()` + paginação/sort | Tabela de dados brutos |
| 3366–3625 | Utilitários, briefing IA, exportações | `mostrarLoader`, `exportarJSON`, `exportarCSV`, integração Claude |
| 3628–3631 | Service Worker | `navigator.serviceWorker.register('sw.js')` |
| 3677 | Footer + fim de `<body>` | Branding "Powered by Luan Guilherme Lourenço" |

---

## Variáveis de Estado Global (app.js, ~linha 1866)

```js
// Dataset principal
let _dadosOriginais = [];          // array de objetos — nunca modificar diretamente
let _headers        = [];          // cabeçalhos originais do arquivo
let _cols           = {};          // { valor, data, vencimento, entidade, chave, categoria, tipo }
let _nomeArquivo    = '';
let _erpDetectado   = null;        // { erp, nome, mapa } ou null

// Charts — SEMPRE destruir antes de recriar
let _chartAging        = null;
let _chartFluxoM       = null;
let _chartComparativo  = null;

// Cache dos últimos cálculos (consumido pelo briefing IA)
let _ultimosKpis = null;
let _ultimaAuditoria = null;
let _ultimoAging = null;
let _ultimoDre = null;
let _ultimoPareto = null;
let _ultimoAntiFraude = null;
let _ultimaAnaliseClaude = '';

// UI
let _auditConfirmados      = new Set();   // problemas marcados como "OK pelo usuário"
let _dashboardVisivel      = false;
let _deferredInstallPrompt = null;        // PWA beforeinstallprompt
let _toastTimer            = null;
let _analisandoAgora       = false;       // lock anti reentrância em executarAnalise()

// Comparativo (segundo dataset)
let _colsComparativos  = null;
let _kpisComparativos  = null;
let _nomeArquivoComp   = '';

// Tabela de dados
let _sortCol = null;
let _sortDir = 'asc';
let _paginaAtual     = 1;
let _dadosVisivelArr = [];
let _todasAbas       = {};                // múltiplas abas do XLSX
```

> Removidos do mapa original: `_dadosFiltrados` (substituído por filtragem inline em `_dadosVisivelArr`).

---

## Fluxo de Dados

```
arquivo (XLSX/CSV/OFX) → carregarArquivo()
  → SheetJS (ou parseOFX se .ofx) → _headers + _dadosOriginais + _todasAbas
  → detectarColunas(_headers) → sugestão automática
  → detectarERP(_headers) → _erpDetectado (se houver match)
  → mostrarConfigColunas(_headers, cols, erpDetectado) → selects de mapeamento
  → [usuário confirma]
  → executarAnalise() (async)
      → lerColsSelecionadas() → aplica MAPAS_ERP_JS se ERP selecionado → _cols
      → calcularKPIs / auditoria / calcularAging / construirDRE / calcularPareto
        / calcularProjecao / calcularSazonalidade / calcularAntiFraude
        / calcularScoreFinanceiro / calcularIntegridade
      → renderKPIs / renderScoreFinanceiro / renderVerificacao / renderAuditoria
        / renderAging / renderDRE / renderPareto / renderAntiFraude
        / renderFluxoPeriodo / renderTabela
      → (opcional) briefing IA via Claude API → renderiza em #card-claude
```

---

## Variáveis CSS (`:root`, linha 1103)

```css
/* Paleta canônica */
--azul:    #1F4E79;  --azul2:  #2E75B6;  --azul3: #D6E4F0;
--gold:    #C9A84C;  --gold-2: #D4A843;
--verde:   #006100;  --verde-bg:   #C6EFCE;
--amarelo: #9C5700;  --amarelo-bg: #FFEB9C;
--vermelho:#9C0006;  --vermelho-bg:#FFC7CE;
--cinza:   #f4f6f9;  --branco: #fff;
--border:  #E2E8F0;  --text-2: #64748B;  --text-3: #94a3b8;
--radius:  10px;     --radius-sm: 6px;

/* Aliases (mantidos por compatibilidade) */
--navy: #1F4E79;  --bg: #f4f6f9;  --text: #1a1a2e;
--surface: #fff;  --success: #006100;  --danger: #9C0006;
```

Dark mode: override completo em `[data-theme="dark"]` (linha 1122+). Toggle persiste em `localStorage`.
Breakpoints: `900px` (KPIs 3 cols), `600px` (mobile — KPIs 2 cols, toolbar empilhada).

---

## Convenções de Código

- Funções em `analise.js` (linhas 53–1101): recebem dados como parâmetros, **nunca tocam o DOM** e **nunca leem `_` globais**
- Funções `render*()` em `app.js`: **nunca calculam** — só renderizam innerHTML usando `esc()` para sanitizar (XSS)
- IDs HTML: `kebab-case` (ex: `card-aging`, `tbody-dados`)
- IDs de selects: `sel-{tipo}` (ex: `sel-valor`, `sel-data`, `sel-erp-sistema`)
- Prefixo `_` para variáveis de estado global
- Nenhum `console.log` em produção — o obfuscador inclui tudo
- Toda chamada Chart.js deve destruir a instância anterior (`_chart*.destroy()`)

---

## Como Adicionar um Novo ERP

### 1. JavaScript (`index.html`, objeto `MAPAS_ERP_JS` na linha 86)

```js
NOME_ERP: {
  sinais: ['ColunaTipica1', 'ColunaTipica2', 'ColunaTipica3'],
  mapa: {
    'ColunaTipica1': 'NF',
    'ColunaTipica2': 'Valor',
    'ColunaTipica3': 'Cliente',
    'ColunaTipica4': 'Data',
    'ColunaTipica5': 'Vencimento',
  }
}
```

Adicionar nome legível em `NOMES_ERP` (mesmo bloco) e `<option value="NOME_ERP">` no `<select id="sel-erp-sistema">`.

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
| URLs das CDNs (SheetJS, Chart.js) | Versões fixadas — mudança quebra compatibilidade e a CSP |
| CSP meta tag (linha 6) | `connect-src` permite apenas `https://api.anthropic.com` (necessário para o briefing IA); `script-src` libera `cdn.sheetjs.com` e `cdn.jsdelivr.net` |
| Nomes das chaves de `_cols` (`valor`, `data`, `vencimento`, `entidade`, `chave`, `categoria`, `tipo`) | Usadas em todas as funções de análise |
| `MAPA_DRE` (array de `{linha, termos}`) | Qualquer mudança altera o DRE para todos os usuários |
| `_chart*.destroy()` antes de `new Chart()` | Sem isso, múltiplos canvas vazam memória |
| `mostrarLoader(true/false)` nos pontos existentes | Remove feedback visual de carregamento |
| Registro do Service Worker (linha 3628) | Remoção quebra o modo PWA offline |
| Chave Claude API em `sessionStorage` | Persistir em `localStorage` viola a promessa de privacidade |

---

## Pontos de Extensão

| O que adicionar | Onde |
|----------------|------|
| Novo card de análise | Dentro do `<main>`, perto dos `#card-*` (linhas 1738–1829), antes de `<div class="card" id="card-dados">` |
| Nova função de cálculo | Final do bloco `analise.js` (antes da linha 1101), sem DOM, retornando estrutura serializável |
| Novo tipo de gráfico | Copiar padrão de `renderAging()` — destruir instância anterior, criar variável `_chartXxx` |
| Novo campo de mapeamento | Adicionar chave em `_cols`, label em `mostrarConfigColunas()`, uso em `executarAnalise()`, regex em `PADROES_COLUNAS` |
| Novo KPI | Retornar do `calcularKPIs()` e renderizar em `renderKPIs()`; opcionalmente pesar em `calcularScoreFinanceiro()` |
| Nova regra anti-fraude | Adicionar em `calcularAntiFraude()` (linha 784); seguir formato `{ tipo, severidade, descricao, items[] }` |
| Novo cache para briefing IA | Adicionar `_ultimoXxx` em `app.js` e incluir no prompt construído antes da chamada Claude |

---

## ERPs Suportados

Arquivo: `base_conhecimento/__init__.py` → `MAPAS_ERP` (Python) e `MAPAS_ERP_JS` (JS, linha 86 do `index.html`).

| Grupo | ERPs |
|-------|------|
| TOTVS | TOTVS (Protheus), TOTVS_RM, TOTVS_DATASUL |
| Mid-market BR | OMIE, QUESTOR, DOMINIO, SANKHYA, SENIOR, CIGAM, ALTERDATA, LINX, MEGA |
| SAP | SAP_B1 |
| Cloud/SMB | CONTA_AZUL, BLING, TINY, NIBO, GRANATUM, GESTAO_CLICK |
| Fiscal | NFE_XML |

> Total atual: **20 ERPs** — Python (`MAPAS_ERP`) e JS (`MAPAS_ERP_JS`) em paridade.

---

## Pipeline de Deploy

```
push → main
  └─► .github/workflows/deploy.yml
        → testes (pytest + vitest) como gate
        → python3 scripts/obfuscar_html.py index.html dist/index.html
            → javascript-obfuscator (domain-lock: euguilouren.github.io)
        → peaceiris/actions-gh-pages → branch gh-pages
        → GitHub Pages serve gh-pages
```

`dist/` está no `.gitignore` — nunca comitar manualmente.
`index.html` é a única fonte — editável localmente e entrada do pipeline.

---

## CI/CD

| Workflow | O que faz |
|----------|-----------|
| `ci.yml` | Matriz pytest Python 3.10/3.11/3.12 + vitest JS, validação de HTML (DOCTYPE, branding) e do `config.yaml`, `pip-audit` |
| `deploy.yml` | Gate de testes → obfusca → publica em `gh-pages` |
| `lighthouse.yml` | Auditoria Lighthouse em push/PR |
| `auto-review.yml` | Code review semanal (segunda 08:00 UTC) via Claude, abre PR opcional |

---

## Suítes de Teste

- **Python (pytest)** — testes unitários em `tests/`
- **JavaScript (vitest)** — 98 testes em `tests/js/` cobrindo as funções puras de `analise.js`: `detectarColunas`, `auditoria`, `calcularAging`, `calcularPareto`, `construirDRE`, `calcularKPIs`, `calcularProjecao`, `calcularSazonalidade`

Rodar localmente:
```bash
npx vitest run                # JS
python3 -m pytest tests/ -q  # Python
```
