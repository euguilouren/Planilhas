import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import vm from 'vm';

const __dirname = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(__dirname, '../../../index.html'), 'utf-8');

// Extract first <script> block with content (analise.js — pure functions, no DOM)
// Skip inline script tags that are src= or type=application/ld+json
const scriptMatch = html.match(/<script>([\s\S]*?)<\/script>/);
if (!scriptMatch) throw new Error('Could not find first <script> block in index.html');
const code = scriptMatch[1];

// Minimal browser-like globals the functions need.
// esc() is defined in app.js (second script block) but referenced in calcularAntiFraude;
// provide a stub so the module loads cleanly.
const ctx = vm.createContext({
  Intl,
  Date,
  Math,
  RegExp,
  Number,
  Array,
  Object,
  String,
  Boolean,
  Set,
  Map,
  TextDecoder,
  Uint8Array,
  console,
  isNaN,
  isFinite,
  parseFloat,
  parseInt,
  NaN,
  Infinity,
  undefined,
  // DOM stubs — renderFluxoPeriodo and window.switchFluxo touch the DOM
  document: {
    getElementById: () => null,
    querySelectorAll: () => [],
  },
  window: {},
  requestAnimationFrame: () => {},
  // esc is defined in the second script block; stub it here
  esc: (v) => String(v ?? ''),
});

vm.runInContext(code, ctx);

export const {
  detectarColunas,
  detectarERP,
  toNum,
  toDate,
  fmtBRL,
  auditoria,
  calcularAging,
  calcularPareto,
  construirDRE,
  calcularKPIs,
  calcularFluxoPeriodo,
  calcularProjecao,
  calcularSazonalidade,
  calcularAntiFraude,
  calcularScoreFinanceiro,
  calcularKPIsComparativo,
  calcularIntegridade,
  parseOFX,
  PADROES_COLUNAS,
  MAPA_DRE,
  MAPAS_ERP_JS,
  _decodeTextBuffer,
  _decodeOFXBuffer,
} = ctx;
