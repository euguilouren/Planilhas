import { describe, it, expect } from 'vitest';
import { _csvEsc } from './helpers/extract-analise.js';

describe('_csvEsc — anti CSV/Formula injection (OWASP)', () => {
  it('valor benigno passa intacto', () => {
    expect(_csvEsc('hello')).toBe('hello');
    expect(_csvEsc('123 ABC')).toBe('123 ABC');
    expect(_csvEsc('R$ 1.234,56')).toBe('R$ 1.234,56');
  });

  // Regressão bug #3 — header injection no exportarCSV. Antes os headers
  // passavam crus; planilha de origem com coluna "=HYPERLINK(...)" virava
  // fórmula executável ao abrir o CSV exportado no Excel.
  it('regressão BUG: fórmula iniciada com = é prefixada com aspa', () => {
    expect(_csvEsc('=SUM(A:A)')).toBe("'=SUM(A:A)");
    expect(_csvEsc('=HYPERLINK("http://evil.com","clique")')).toBe(
      "'=HYPERLINK(\"http://evil.com\",\"clique\")"
    );
    expect(_csvEsc('=cmd|\'/C calc\'!A1')).toBe("'=cmd|'/C calc'!A1");
  });

  it('fórmula iniciada com + é prefixada', () => {
    expect(_csvEsc('+SUM(A1)')).toBe("'+SUM(A1)");
  });

  it('fórmula iniciada com - é prefixada', () => {
    expect(_csvEsc('-1+cmd')).toBe("'-1+cmd");
  });

  it('@ no início (Lotus/legacy) é prefixado', () => {
    expect(_csvEsc('@SUM(1,2)')).toBe("'@SUM(1,2)");
  });

  it('tab/CR no início é prefixado (escape de separador)', () => {
    expect(_csvEsc('\t=evil')).toBe("'\t=evil");
    expect(_csvEsc('\r=evil')).toBe("'\r=evil");
  });

  it('caractere especial NO MEIO da célula NÃO é escapado', () => {
    expect(_csvEsc('R$ 100=5')).toBe('R$ 100=5');
    expect(_csvEsc('email@test.com')).toBe('email@test.com');
    expect(_csvEsc('1+1=2')).toBe('1+1=2');
  });

  it('null/undefined viram string vazia', () => {
    expect(_csvEsc(null)).toBe('');
    expect(_csvEsc(undefined)).toBe('');
  });

  it('número positivo passa como string', () => {
    expect(_csvEsc(42)).toBe('42');
    expect(_csvEsc(0)).toBe('0');
  });

  it('número negativo é prefixado (tradeoff defensive contra injection)', () => {
    // -1.5 vira "-1.5" via String() → casa /^[\-]/ → prefixado.
    // Excel interpreta aspa simples como "literal texto" e mostra "-1.5" sem aspa.
    // Tradeoff conhecido: valores numéricos negativos no CSV podem aparecer
    // como texto em parsers strict, mas previne =cmd injection se valor
    // começar com "-=cmd".
    expect(_csvEsc(-1.5)).toBe("'-1.5");
    expect(_csvEsc(-100)).toBe("'-100");
  });

  it('strings vazias ou só whitespace passam', () => {
    expect(_csvEsc('')).toBe('');
    expect(_csvEsc('   ')).toBe('   ');
  });

  it('headers reais de ERP não disparam falso-positivo', () => {
    expect(_csvEsc('Valor')).toBe('Valor');
    expect(_csvEsc('Data de Emissão')).toBe('Data de Emissão');
    expect(_csvEsc('Cliente / Fornecedor')).toBe('Cliente / Fornecedor');
    expect(_csvEsc('NF-2024-001')).toBe('NF-2024-001');
  });
});
