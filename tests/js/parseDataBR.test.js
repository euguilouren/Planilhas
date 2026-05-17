import { describe, it, expect } from 'vitest';
import { _parseDataBR } from './helpers/extract-analise.js';

describe('_parseDataBR', () => {
  it('null/undefined/vazio retornam null', () => {
    expect(_parseDataBR(null)).toBeNull();
    expect(_parseDataBR(undefined)).toBeNull();
    expect(_parseDataBR('')).toBeNull();
    expect(_parseDataBR(0)).toBeNull();
  });

  it('DD/MM/YYYY string vira YYYY-MM-DD', () => {
    expect(_parseDataBR('15/03/2024')).toBe('2024-03-15');
    expect(_parseDataBR('01/12/2025')).toBe('2025-12-01');
  });

  it('YYYY-MM-DD string passa direto', () => {
    expect(_parseDataBR('2024-03-15')).toBe('2024-03-15');
  });

  it('YYYY-MM-DD com timestamp ignora hora', () => {
    expect(_parseDataBR('2024-03-15T10:30:00')).toBe('2024-03-15');
  });

  it('Date object vira ISO local', () => {
    const d = new Date(2024, 2, 15); // 15 mar 2024 local
    expect(_parseDataBR(d)).toBe('2024-03-15');
  });

  it('Date inválido retorna null', () => {
    expect(_parseDataBR(new Date('lixo'))).toBeNull();
  });

  // Regressão bug #7 — antes: Excel serial usava getFullYear()/getMonth()/
  // getDate() (LOCAL) num Date criado de ms UTC, perdendo um dia em UTC-3.
  // Fix: getUTC* — alinha com toDate em analise.js.
  it('regressão BUG: Excel serial 45366 vira 2024-03-15 (não 03-14)', () => {
    // 45366 = 15 mar 2024 em Excel (origem 1900)
    // Sem fix: em UTC-3 retornava "2024-03-14" — filtro de=15/03 excluía dia 15
    expect(_parseDataBR(45366)).toBe('2024-03-15');
  });

  it('Excel serial 1 retorna 1899-12-31 (sem compensar o bug histórico 1900)', () => {
    // Excel define 1 = 1900-01-01 mas inclui o falso 29/fev/1900 (bug
    // mantido por compat com Lotus). _parseDataBR — assim como toDate —
    // usa epoch 25569 sem compensação, então serial baixos têm offset
    // de 1 dia. Tradeoff aceito: datas reais financeiras são 1995+.
    expect(_parseDataBR(1)).toBe('1899-12-31');
  });

  it('Excel serial inválido (Infinity) retorna null', () => {
    expect(_parseDataBR(Infinity)).toBeNull();
  });

  it('formato não reconhecido retorna null', () => {
    expect(_parseDataBR('Mar 15')).toBeNull();
    expect(_parseDataBR('lixo')).toBeNull();
    expect(_parseDataBR('15-03-2024')).toBeNull();
  });

  it('comparação string-lexicográfica funciona para filtro de data', () => {
    // ISO YYYY-MM-DD compara como string corretamente
    const a = _parseDataBR('15/03/2024');
    const b = _parseDataBR('20/03/2024');
    expect(a < b).toBe(true);
    expect(b > a).toBe(true);
  });
});
