import { describe, it, expect } from 'vitest';
import { construirDRE } from './helpers/extract-analise.js';

function makeRow(cat, valor) {
  return { Categoria: cat, Valor: valor };
}

describe('construirDRE', () => {
  it('returns null when colValor is missing', () => {
    expect(construirDRE([makeRow('RECEITA', 1000)], 'Categoria', null)).toBeNull();
    expect(construirDRE([makeRow('RECEITA', 1000)], 'Categoria', undefined)).toBeNull();
  });

  it('returns object with linhas and modo', () => {
    const dados = [makeRow('RECEITA', 1000), makeRow('DESPESA', -200)];
    const result = construirDRE(dados, 'Categoria', 'Valor');
    expect(result).not.toBeNull();
    expect(Array.isArray(result.linhas)).toBe(true);
    expect(typeof result.modo).toBe('string');
  });

  it('modo is "categoria" when colCat is provided', () => {
    const dados = [makeRow('RECEITA', 500)];
    const result = construirDRE(dados, 'Categoria', 'Valor');
    expect(result.modo).toBe('categoria');
  });

  it('modo is "sinal" when colCat is null', () => {
    const dados = [{ Valor: 500 }, { Valor: -100 }];
    const result = construirDRE(dados, null, 'Valor');
    expect(result.modo).toBe('sinal');
  });

  it('sinal mode: positive values go to Receita Bruta', () => {
    const dados = [{ Valor: 1000 }, { Valor: 500 }];
    const result = construirDRE(dados, null, 'Valor');
    const rb = result.linhas.find(l => l.linha === 'Receita Bruta');
    expect(rb).toBeDefined();
    expect(rb.valor).toBeCloseTo(1500, 2);
  });

  it('sinal mode: negative values go to Despesas Operacionais', () => {
    const dados = [{ Valor: -300 }, { Valor: -100 }];
    const result = construirDRE(dados, null, 'Valor');
    const desp = result.linhas.find(l => l.linha === '(-) Despesas Operacionais');
    expect(desp).toBeDefined();
    expect(desp.valor).toBeCloseTo(-400, 2);
  });

  it('linhas array has expected DRE structure fields', () => {
    const dados = [makeRow('RECEITA', 2000), makeRow('CMV', -500)];
    const result = construirDRE(dados, 'Categoria', 'Valor');
    result.linhas.forEach(l => {
      expect(typeof l.linha).toBe('string');
      expect(typeof l.valor).toBe('number');
      expect(typeof l.tipo).toBe('string');
    });
  });

  it('contains standard DRE summary lines', () => {
    const dados = [makeRow('RECEITA', 1000)];
    const result = construirDRE(dados, 'Categoria', 'Valor');
    const linhaNames = result.linhas.map(l => l.linha);
    expect(linhaNames).toContain('Receita Bruta');
    expect(linhaNames).toContain('(=) Receita Líquida');
    expect(linhaNames).toContain('(=) Lucro Bruto');
    expect(linhaNames).toContain('(=) EBIT (Resultado Operacional)');
    expect(linhaNames).toContain('(=) Lucro Líquido');
  });

  it('lucro líquido equals receita bruta with no deductions or costs', () => {
    const dados = [makeRow('RECEITA', 5000)];
    const result = construirDRE(dados, 'Categoria', 'Valor');
    const ll = result.linhas.find(l => l.linha === '(=) Lucro Líquido');
    expect(ll.valor).toBeCloseTo(5000, 2);
  });

  it('ignores rows with NaN values', () => {
    const dados = [makeRow('RECEITA', 1000), { Categoria: 'RECEITA', Valor: 'abc' }];
    const result = construirDRE(dados, 'Categoria', 'Valor');
    const rb = result.linhas.find(l => l.linha === 'Receita Bruta');
    expect(rb.valor).toBeCloseTo(1000, 2);
  });

  it('returns valid result for empty dados', () => {
    const result = construirDRE([], 'Categoria', 'Valor');
    expect(result).not.toBeNull();
    const ll = result.linhas.find(l => l.linha === '(=) Lucro Líquido');
    expect(ll.valor).toBeCloseTo(0, 2);
  });

  // Regressão: quando rl=0 (dataset só com despesas), AV% antes
  // retornava 0 pra todas as linhas — falso "estrutura zerada".
  // Agora retorna NaN para o render mostrar '—'.
  it('AV% retorna NaN quando Receita Líquida é zero (só despesas)', () => {
    const dados = [
      makeRow('DESPESA OPERACIONAL', -1000),
      makeRow('DESPESA OPERACIONAL', -500),
    ];
    const result = construirDRE(dados, 'Categoria', 'Valor');
    for (const linha of result.linhas) {
      expect(Number.isNaN(linha.av)).toBe(true);
    }
  });

  it('AV% é numérico finito quando há Receita Líquida', () => {
    const dados = [
      makeRow('RECEITA', 1000),
      makeRow('DESPESA OPERACIONAL', -300),
    ];
    const result = construirDRE(dados, 'Categoria', 'Valor');
    const rb = result.linhas.find(l => l.linha === 'Receita Bruta');
    expect(Number.isFinite(rb.av)).toBe(true);
    expect(rb.av).toBeCloseTo(100, 1);
  });

  // Regressão: "DESPESA FINANCEIRA" antes caía em (-) Despesas Operacionais
  // porque /DESPESA/ matchava antes de /FINANCEI/. Isso distorcia EBIT — por
  // norma o EBIT exclui o resultado financeiro. Fix: Resultado Financeiro
  // vem antes de Despesas Operacionais no MAPA_DRE.
  it('regressão BUG: "DESPESA FINANCEIRA" classifica em Resultado Financeiro, não Despesas Operacionais', () => {
    const dados = [
      makeRow('RECEITA DE VENDAS', 10000),
      makeRow('DESPESA FINANCEIRA', -2000),
      makeRow('DESPESA OPERACIONAL', -1000),
    ];
    const result = construirDRE(dados, 'Categoria', 'Valor');
    const dop = result.linhas.find(l => l.linha === '(-) Despesas Operacionais');
    const rf  = result.linhas.find(l => l.linha === '(-/+) Resultado Financeiro');
    // -1000 só (operacional pura). NÃO deve incluir a despesa financeira.
    expect(dop.valor).toBeCloseTo(-1000, 2);
    // -2000 (despesa financeira), preservada com sinal.
    expect(rf.valor).toBeCloseTo(-2000, 2);
    // EBIT = LB - DOP = (10000 - 0 - 0) - 1000 = 9000 (sem deduzir financeiro)
    const ebit = result.linhas.find(l => l.linha === '(=) EBIT (Resultado Operacional)');
    expect(ebit.valor).toBeCloseTo(9000, 2);
    // Lucro antes IR = EBIT + RF = 9000 + (-2000) = 7000
    const lair = result.linhas.find(l => l.linha === '(=) Resultado antes IR/CSLL');
    expect(lair.valor).toBeCloseTo(7000, 2);
  });

  it('regressão BUG: "JUROS DE EMPRÉSTIMO" classifica em Resultado Financeiro', () => {
    const dados = [
      makeRow('RECEITA', 5000),
      makeRow('JUROS DE EMPRÉSTIMO', -800),
    ];
    const result = construirDRE(dados, 'Categoria', 'Valor');
    const rf = result.linhas.find(l => l.linha === '(-/+) Resultado Financeiro');
    expect(rf.valor).toBeCloseTo(-800, 2);
  });
});
