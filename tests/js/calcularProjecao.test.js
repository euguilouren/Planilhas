import { describe, it, expect } from 'vitest';
import { calcularProjecao } from './helpers/extract-analise.js';

// Build linhas similar to what calcularFluxoPeriodo returns
function makeLinhas(n, recBase, despBase, step = 0) {
  return Array.from({ length: n }, (_, i) => ({
    periodo: `${String((i % 12) + 1).padStart(2, '0')}/2024`,
    receita: recBase + step * i,
    despesa: despBase,
    resultado: recBase + step * i - despBase,
    nfRec: 10,
    nfDesp: 5,
    pct: 0,
  }));
}

describe('calcularProjecao', () => {
  it('returns null for empty input', () => {
    expect(calcularProjecao([], 3)).toBeNull();
  });

  it('returns null for less than 3 data points', () => {
    expect(calcularProjecao(makeLinhas(1, 100, 50), 3)).toBeNull();
    expect(calcularProjecao(makeLinhas(2, 100, 50), 3)).toBeNull();
  });

  it('returns nProjecoes items', () => {
    const linhas = makeLinhas(6, 1000, 500);
    const result = calcularProjecao(linhas, 3);
    expect(result).toHaveLength(3);
  });

  it('returns 4 projected items when nProjecoes = 4', () => {
    const linhas = makeLinhas(6, 1000, 500);
    const result = calcularProjecao(linhas, 4);
    expect(result).toHaveLength(4);
  });

  it('all projected items have projetado: true', () => {
    const linhas = makeLinhas(6, 1000, 500);
    const result = calcularProjecao(linhas, 3);
    result.forEach(item => {
      expect(item.projetado).toBe(true);
    });
  });

  it('projected items have numeric rec, desp, res', () => {
    const linhas = makeLinhas(6, 1000, 500);
    const result = calcularProjecao(linhas, 3);
    result.forEach(item => {
      expect(typeof item.rec).toBe('number');
      expect(typeof item.desp).toBe('number');
      expect(typeof item.res).toBe('number');
      expect(isNaN(item.rec)).toBe(false);
      expect(isNaN(item.desp)).toBe(false);
      expect(isNaN(item.res)).toBe(false);
    });
  });

  it('projected items have string periodo labels', () => {
    const linhas = makeLinhas(6, 1000, 500);
    const result = calcularProjecao(linhas, 3);
    result.forEach(item => {
      expect(typeof item.periodo).toBe('string');
      expect(item.periodo.length).toBeGreaterThan(0);
    });
  });

  it('res equals rec minus desp for each projection', () => {
    const linhas = makeLinhas(6, 1000, 500);
    const result = calcularProjecao(linhas, 3);
    result.forEach(item => {
      expect(item.res).toBeCloseTo(item.rec - item.desp, 2);
    });
  });

  it('perfectly constant series produces stable projections', () => {
    // All same value → linear regression slope = 0, projection = mean
    const linhas = makeLinhas(6, 1000, 400);
    const result = calcularProjecao(linhas, 3);
    result.forEach(item => {
      expect(item.rec).toBeCloseTo(1000, 0);
      expect(item.desp).toBeCloseTo(400, 0);
    });
  });

  it('strictly increasing series produces increasing projections', () => {
    // Receita increases by 100 each period
    const linhas = makeLinhas(6, 1000, 500, 100);
    const result = calcularProjecao(linhas, 3);
    // All projected revenues should be >= initial value (trend is up)
    result.forEach(item => {
      expect(item.rec).toBeGreaterThan(0);
    });
    // Later projections should be >= earlier ones (monotone in linear extrapolation)
    expect(result[1].rec).toBeGreaterThanOrEqual(result[0].rec);
    expect(result[2].rec).toBeGreaterThanOrEqual(result[1].rec);
  });

  it('uses default nProjecoes of 3 when not provided', () => {
    const linhas = makeLinhas(6, 1000, 500);
    const result = calcularProjecao(linhas);
    expect(result).toHaveLength(3);
  });

  it('regressão BUG: parser de período aceita formato DD/MM/YYYY (freq=D)', () => {
    // calcularFluxoPeriodo com freq='D' emite "DD/MM/YYYY"
    const linhas = Array.from({ length: 5 }, (_, i) => ({
      periodo: `${String(i + 1).padStart(2, '0')}/03/2024`,
      receita: 100, despesa: 50, resultado: 50, nfRec: 1, nfDesp: 1, pct: 0,
    }));
    const result = calcularProjecao(linhas, 3);
    // Última data é 05/03/2024 → mês base = março (idx 2)
    // Projeção começa em Abr → primeiro item: Abr/2024, depois Mai/2024, Jun/2024
    expect(result[0].periodo).toBe('Abr/2024');
    expect(result[1].periodo).toBe('Mai/2024');
    expect(result[2].periodo).toBe('Jun/2024');
  });

  it('regressão BUG: parser de período aceita formato YYYY (freq=A)', () => {
    // calcularFluxoPeriodo com freq='A' emite só "YYYY"
    const linhas = [
      { periodo: '2022', receita: 100, despesa: 50, resultado: 50, nfRec: 1, nfDesp: 1, pct: 0 },
      { periodo: '2023', receita: 110, despesa: 50, resultado: 60, nfRec: 1, nfDesp: 1, pct: 0 },
      { periodo: '2024', receita: 120, despesa: 50, resultado: 70, nfRec: 1, nfDesp: 1, pct: 0 },
    ];
    const result = calcularProjecao(linhas, 3);
    // Para freq=A: baseAno=2024, baseMes=11 (dez) → projeção continua jan/fev/mar do ano seguinte
    expect(result[0].periodo).toBe('Jan/2025');
    expect(result[1].periodo).toBe('Fev/2025');
    expect(result[2].periodo).toBe('Mar/2025');
  });

  it('regressão BUG: fallback robusto se periodo for inválido', () => {
    const linhas = [
      { periodo: 'lixo', receita: 100, despesa: 50, resultado: 50, nfRec: 1, nfDesp: 1, pct: 0 },
      { periodo: 'mais', receita: 110, despesa: 50, resultado: 60, nfRec: 1, nfDesp: 1, pct: 0 },
      { periodo: 'lixo', receita: 120, despesa: 50, resultado: 70, nfRec: 1, nfDesp: 1, pct: 0 },
    ];
    const result = calcularProjecao(linhas, 3);
    // baseAno cai para new Date().getFullYear() (não NaN), baseMes=0
    expect(result).toHaveLength(3);
    result.forEach(item => {
      expect(typeof item.periodo).toBe('string');
      expect(item.periodo).not.toContain('NaN');
      expect(item.periodo).not.toContain('undefined');
    });
  });
});
