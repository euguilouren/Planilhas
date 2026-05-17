import { describe, it, expect } from 'vitest';
import { _formatCellValue } from './helpers/extract-analise.js';

describe('_formatCellValue', () => {
  it('Date object vira DD/MM/YYYY (não US verbose)', () => {
    // Regressão bugs #6 e #10 — antes: "Mon Mar 15 2024 GMT-0300..."
    const d = new Date(2024, 2, 15); // 15 mar 2024
    const out = _formatCellValue(d);
    expect(out).toMatch(/15\/03\/2024|15\/3\/2024/);
    expect(out).not.toMatch(/Mon|GMT|Tue|Wed/);
  });

  it('string passa identity', () => {
    expect(_formatCellValue('hello')).toBe('hello');
    expect(_formatCellValue('123 ABC')).toBe('123 ABC');
  });

  it('número vira String', () => {
    expect(_formatCellValue(42)).toBe('42');
    expect(_formatCellValue(0)).toBe('0');
    expect(_formatCellValue(-1.5)).toBe('-1.5');
  });

  it('null/undefined retornam fallback (default vazio)', () => {
    expect(_formatCellValue(null)).toBe('');
    expect(_formatCellValue(undefined)).toBe('');
  });

  it('null/undefined com fallback customizado', () => {
    expect(_formatCellValue(null, '—')).toBe('—');
    expect(_formatCellValue(undefined, 'N/A')).toBe('N/A');
  });

  it('Date inválida ainda retorna fmtData (— por design de fmtData)', () => {
    // fmtData() retorna '—' para valores falsy, mas instanceof Date passa
    // o Date inválido para fmtData — que retorna formato do navegador.
    // Não bug: Date inválido em _dadosOriginais é caso degenerado.
    const d = new Date('lixo');
    const out = _formatCellValue(d);
    expect(typeof out).toBe('string');
  });

  it('string vazia retorna string vazia (não fallback)', () => {
    // v == null cobre só null/undefined — '' passa por String('')
    expect(_formatCellValue('')).toBe('');
    expect(_formatCellValue('', '—')).toBe('');
  });

  it('0 retorna "0" (não falsy fallback)', () => {
    expect(_formatCellValue(0)).toBe('0');
    expect(_formatCellValue(0, '—')).toBe('0');
  });

  it('false retorna "false"', () => {
    expect(_formatCellValue(false)).toBe('false');
  });
});
