# CLAUDE.md — FluxoPRO

> Guia de arquitetura para refinamentos. Leia antes de qualquer edição.

## Arquitetura em uma linha

`index.html` é o produto inteiro (~3779 linhas, monolítico). Python é backend opcional não usado no GitHub Pages.
Análise 100% client-side: SheetJS lê XLSX/CSV (+ OFX nativo via `parseOFX`), Chart.js renderiza aging/fluxo/comparativo, Service Worker (`sw.js`) entrega PWA offline, CSP restringe execução. Briefing IA via Claude API é opcional — chave fica em `sessionStorage`, nunca persistida.

---

## Mapa de Seções do index.html

| Linhas | Bloco | Responsabilidade |
|--------|-------|-----------------|
| 3–52 | `<head>` + CDNs + CSP | CSP meta (linha 6), SheetJS 0.20.3, Chart.js 4.4.0, JSON-LD schema.org |
| 53–1190 | `<script>` analise.js | Módulos **puros de cálculo** + utilitários — sem DOM, sem `_` globais |
| 64–82 | `PADROES_COLUNAS` + `detectarColunas()` | Regex genéricas (valor, data, vencimento, entidade, chave, categoria, tipo) |
| 86–130 | `MAPAS_ERP_JS` + `NOMES_ERP` + `detectarERP()` | 20 ERPs com `sinais`/`mapa` — aplicado em `lerColsSelecionadas()` |
| 132–203 | `calcularIntegridade()` | Verificação cruzada (soma, contagens, KPIs vs. amostra) |
| 205–293 | `toNum`, `toDate`, `fmtBRL`, `fmtNum`, `fmtData` | Parsers e formatters puros (PT-BR, US, parênteses contábeis, ISO/BR datas, Excel serial UTC) |
| 295–333 | `_formatCellValue` + `_parseDataBR` + `_csvEsc` | Helpers compartilhados entre app.js e analise.js. `_csvEsc` previne CSV injection (OWASP); `_parseDataBR` usa `getUTC*` p/ evitar day-1 em UTC-3; `_formatCellValue` centraliza Date→fmtData |
| 335–443 | `auditoria()` | Duplicatas, campos vazios, outliers, datas futuras (skip DEVOLUÇÃO/ESTORNO) |
| 445–485 | `calcularAging()` | Aging de recebíveis em 5 faixas |
| 487–522 | `calcularPareto()` | Top N entidades com % acumulado |
| 524–600 | `MAPA_DRE` + `construirDRE()` | Monta DRE por regex de categorias. **Resultado Financeiro + IR/CSLL antes de Despesas Operacionais** (loop com break — DESPESA FINANCEIRA precisa match `/FINANCEI/` antes de `/DESPESA/`) |
| 602–638 | `calcularKPIs()` | KPIs financeiros + período min/max |
| 640–688 | `calcularFluxoPeriodo()` | Buckets D/M/A — só cria grupo quando valor válido (sem fantasma R$0) |
| 690–731 | `calcularProjecao()` | Regressão linear; parser aceita `MM/YYYY`, `DD/MM/YYYY`, `YYYY` |
| 733–763 | `calcularSazonalidade()` | Padrões mensais/semanais |
| 765–844 | `renderFluxoPeriodo()` | Render do fluxo (vive em analise.js por histórico) |
| 846–1061 | `calcularAntiFraude()` + constantes Benford/χ² | 12+ regras: duplicatas (exata+fuzzy), round-numbers, fracionamento, Benford, anomalias temporais (fins de semana, feriados BR) |
| 1063–1104 | `calcularScoreFinanceiro()` | Score 0–100 ponderado (margem + aging + Pareto + auditoria) |
| 1106–1119 | `calcularKPIsComparativo()` | Delta de KPIs entre 2 datasets |
| 1121–1156 | `_decodeTextBuffer()` + `_decodeOFXBuffer()` | Probe UTF-8 → fallback windows-1252 (bancos BR legacy: Itaú, Bradesco, Santander) |
| 1158–1190 | `parseOFX()` | Parser nativo SGML + XML 2.x |
| 1191–1678 | `<style>` | CSS completo — `:root`, layout, responsivo, dark mode (`[data-theme="dark"]`) |
| 1680–1946 | `<body>` HTML | Header, upload, cards de análise (`#card-*`), painel comparativo, briefing IA, onboarding |
| 1948–3779 | `<script>` app.js | Estado global, eventos, funções render, integração Claude |
| 1985–2014 | Estado global | Ver tabela abaixo |
| 2143–2282 | `carregarArquivo()` | FileReader → `_decodeTextBuffer` (CSV) ou SheetJS/OFX → `detectarColunas()` → `detectarERP()` → `mostrarConfigColunas()`. **Lock `_analisandoAgora` no início** previne race |
| 2300–2365 | `carregarArquivoComparativo()` | Mesmo fluxo p/ segundo dataset; também sob lock `_analisandoAgora` |
| 2367–2436 | `mostrarConfigColunas()` + `_atualizarPreview` + `aplicarMapeamentoERP` + `lerColsSelecionadas` | Selects de mapeamento + aplicação do ERP detectado. `_atualizarPreview` usa `_formatCellValue` (não String) |
| 2440–2553 | `executarAnalise()` | Orquestra módulos + chama todos os render (async — `await _yield()` solta thread; lock `_analisandoAgora` evita reentrância) |
| 2561–2605 | `renderKPIs()` | Cards KPI |
| 2607–2696 | `renderScoreFinanceiro()` | Score 0–100 com componentes |
| 2698–2736 | `renderVerificacao()` | Painel de integridade |
| 2738–2792 | `renderAuditoria()` + `_auditoriaPendentes` | Tabela de problemas com badges + confirmação |
| 2794–2855 | `renderAging()` | Barras + Chart.js (destruir `_chartAging` antes) |
| 2857–2900 | `renderDRE()` | Tabela DRE com cores por tipo + AV% (NaN→'—' quando RL=0) |
| 2902–2929 | `renderPareto()` | Tabela Pareto com badge Classe A |
| 2931–3013 | `renderComparativo()` | Tabela + Chart.js (`_chartComparativo`) |
| 3015–3095 | `renderAntiFraude()` | Alertas de fraude agrupados |
| 3097–3245 | `renderTabela()` + `filtrarTabela()` + paginação/sort | Tabela de dados brutos. `renderTabela` usa `_formatCellValue` em células; `filtrarTabela` idem na busca |
| 3247–3528 | Briefing IA + onboarding + histórico | `_gerarBriefing`, `_markdownParaHTML`, `analisarComClaude`, `_mostrarOnboarding`, `_salvarHistorico` |
| 3529–3567 | `exportarJSON()` + `exportarCSV()` | Exports. `exportarCSV` usa `_csvEsc` em **headers e células** |
| 3569–3645 | `_trocarAba()` | Multi-sheet XLSX. Lock `_analisandoAgora`, destroi charts, esconde dashboard, reset paginação |
| 3678–3681 | Service Worker | `navigator.serviceWorker.register('sw.js')` |
| 3779 | Footer + fim de `<body>` | Branding "Powered by Luan Guilherme Lourenço" |

---

## Variáveis de Estado Global (app.js, ~linha 1985)

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

## Variáveis CSS (`:root`, linha 1192)

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

Dark mode: override completo em `[data-theme="dark"]` (linha ~1211). Toggle persiste em `localStorage`.
Breakpoints: `900px` (KPIs 3 cols), `600px` (mobile — KPIs 2 cols, toolbar empilhada).

---

## Convenções de Código

- Funções em `analise.js` (linhas 53–1190): recebem dados como parâmetros, **nunca tocam o DOM** e **nunca leem `_` globais**. Inclui também helpers compartilhados (`_formatCellValue`, `_parseDataBR`, `_csvEsc`) — puros, testáveis em vitest, acessíveis ao app.js via escopo de janela
- Funções `render*()` em `app.js`: **nunca calculam** — só renderizam innerHTML usando `esc()` para sanitizar (XSS)
- Para exibir valor de célula em DOM/preview, use `_formatCellValue(v)` em vez de `String(v)` — trata Date object (XLSX cellDates) → DD/MM/YYYY em vez de "Mon Mar 15 2024 GMT-0300..."
- IDs HTML: `kebab-case` (ex: `card-aging`, `tbody-dados`)
- IDs de selects: `sel-{tipo}` (ex: `sel-valor`, `sel-data`, `sel-erp-sistema`)
- Prefixo `_` para variáveis de estado global
- Nenhum `console.log` em produção — o obfuscador inclui tudo
- Toda chamada Chart.js deve destruir a instância anterior (`_chart*.destroy()`)
- Operações async em `executarAnalise`, `carregarArquivo*`, `_trocarAba` checam o lock `_analisandoAgora` — não criar novos handlers de UI que mutem `_dadosOriginais`/`_cols` sem o guarda

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
| Registro do Service Worker (linha 3678) | Remoção quebra o modo PWA offline |
| Ordem do `MAPA_DRE` (Resultado Financeiro e IR/CSLL antes de Despesas Operacionais) | Loop com `break` no primeiro match — reordenar fará `DESPESA FINANCEIRA` cair em DespOp e distorcer EBIT |
| `_csvEsc` aplicado em **headers** e células do `exportarCSV` | Remover do header reintroduz CSV/Formula injection — planilha com coluna `=HYPERLINK(...)` vira fórmula no Excel |
| `_parseDataBR` usa `getUTC*` para Excel serial | Trocar por `getFullYear()` reintroduz day-1 bug em UTC-3 |
| `_analisandoAgora` checado em `_trocarAba`, `carregarArquivo`, `carregarArquivoComparativo` | Sem o guard, troca durante análise corrompe `_ultimosKpis` etc |
| Chave Claude API em `sessionStorage` | Persistir em `localStorage` viola a promessa de privacidade |

---

## Pontos de Extensão

| O que adicionar | Onde |
|----------------|------|
| Novo card de análise | Dentro do `<main>`, perto dos `#card-*` (linhas ~1820–1910), antes de `<div class="card" id="card-dados">` |
| Nova função de cálculo | Final do bloco `analise.js` (antes da linha 1190), sem DOM, retornando estrutura serializável |
| Novo helper puro (parser/format) | Junto de `_formatCellValue` / `_parseDataBR` / `_csvEsc` (~linha 295–333) — exportar via `extract-analise.js` para teste vitest |
| Novo tipo de gráfico | Copiar padrão de `renderAging()` — destruir instância anterior, criar variável `_chartXxx` |
| Novo campo de mapeamento | Adicionar chave em `_cols`, label em `mostrarConfigColunas()`, uso em `executarAnalise()`, regex em `PADROES_COLUNAS` |
| Novo KPI | Retornar do `calcularKPIs()` e renderizar em `renderKPIs()`; opcionalmente pesar em `calcularScoreFinanceiro()` |
| Nova regra anti-fraude | Adicionar em `calcularAntiFraude()` (~linha 866); seguir formato `{ tipo, severidade, descricao, items[] }` |
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
| `ci.yml` | pytest Python 3.12 + vitest JS, validação de HTML (DOCTYPE, branding) e do `config.yaml`, `pip-audit`, `bandit`, SRI dos CDNs |
| `deploy.yml` | Gate de testes → obfusca → publica em `gh-pages` |
| `lighthouse.yml` | Auditoria Lighthouse em push/PR |
| `auto-review.yml` | Code review semanal (segunda 08:00 UTC) via Claude, abre PR opcional |

---

## Suítes de Teste

- **Python (pytest)** — 337 testes em `tests/`
- **JavaScript (vitest)** — 270 testes em `tests/js/` cobrindo todas as funções puras de `analise.js`:
  - Parsers: `toNum`, `toDate`, `_parseDataBR`
  - Helpers de UI: `_formatCellValue`, `_csvEsc`
  - Decoders: `_decodeTextBuffer`, `_decodeOFXBuffer`
  - Detecção: `detectarColunas`, `detectarERP`
  - Cálculo: `auditoria`, `calcularAging`, `calcularPareto`, `construirDRE`, `calcularKPIs`, `calcularFluxoPeriodo`, `calcularProjecao`, `calcularSazonalidade`, `calcularAntiFraude`, `calcularScoreFinanceiro`, `calcularKPIsComparativo`, `calcularIntegridade`
  - Parser: `parseOFX`

Para expor nova função pura ao vitest, exportar em `tests/js/helpers/extract-analise.js` (destructure no final do arquivo).

Rodar localmente:
```bash
npx vitest run                # JS
python3 -m pytest tests/ -q  # Python
```
