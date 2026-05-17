import { describe, it, expect } from 'vitest';
import { _decodeTextBuffer, _decodeOFXBuffer } from './helpers/extract-analise.js';

// Helper: monta ArrayBuffer de bytes literais
const buf = (...bytes) => new Uint8Array(bytes).buffer;

describe('_decodeTextBuffer — fallback UTF-8 → windows-1252', () => {
  it('decodifica UTF-8 puro corretamente', () => {
    // "ação" em UTF-8: 0x61, 0xC3 0xA7, 0xC3 0xA3, 0x6F
    const out = _decodeTextBuffer(buf(0x61, 0xC3, 0xA7, 0xC3, 0xA3, 0x6F));
    expect(out).toBe('ação');
  });

  it('honra BOM UTF-8 e remove na decodificação', () => {
    // BOM + "ab"
    const out = _decodeTextBuffer(buf(0xEF, 0xBB, 0xBF, 0x61, 0x62));
    // BOM aparece como ﻿ no início — caller faz o slice se quiser
    expect(out).toContain('ab');
  });

  it('regressão BUG: cai para windows-1252 quando UTF-8 estrito falha', () => {
    // "ção" em windows-1252/Latin-1: ç=0xE7, ã=0xE3, o=0x6F
    // Esses bytes são inválidos em UTF-8 estrito (sem prefixo de continuação).
    const out = _decodeTextBuffer(buf(0xE7, 0xE3, 0x6F));
    expect(out).toBe('ção');
  });

  it('regressão BUG: CSV Bradesco/Itaú em Latin-1 não vira lixo', () => {
    // "VENCIMENTO" + ";" + "MAUÁ" (Á=0xC1 em windows-1252)
    const bytes = [
      0x56, 0x45, 0x4E, 0x43, 0x49, 0x4D, 0x45, 0x4E, 0x54, 0x4F, 0x3B,
      0x4D, 0x41, 0x55, 0xC1,
    ];
    const out = _decodeTextBuffer(buf(...bytes));
    expect(out).toBe('VENCIMENTO;MAUÁ');
    expect(out).not.toContain('�'); // não pode ter replacement char
  });

  it('texto ASCII puro funciona em ambos os caminhos', () => {
    const out = _decodeTextBuffer(buf(0x48, 0x65, 0x6C, 0x6C, 0x6F));
    expect(out).toBe('Hello');
  });

  it('buffer vazio retorna string vazia', () => {
    expect(_decodeTextBuffer(buf())).toBe('');
  });
});

describe('_decodeOFXBuffer — probe de header antes de fallback', () => {
  it('honra encoding declarado no header XML OFX 2.x', () => {
    // <?xml version="1.0" encoding="UTF-8"?> + "café"
    const header = '<?xml version="1.0" encoding="UTF-8"?>';
    const body = 'café';
    const bytes = [];
    for (const c of header) bytes.push(c.charCodeAt(0));
    // UTF-8 bytes de "café": 0x63, 0x61, 0x66, 0xC3, 0xA9
    bytes.push(0x63, 0x61, 0x66, 0xC3, 0xA9);
    const out = _decodeOFXBuffer(buf(...bytes));
    expect(out).toContain('café');
  });

  it('OFX SGML com ENCODING:UTF-8 é decodificado como UTF-8', () => {
    const header = 'OFXHEADER:100\r\nENCODING:UTF-8\r\n\r\n';
    const bytes = [];
    for (const c of header) bytes.push(c.charCodeAt(0));
    bytes.push(0x63, 0x61, 0x66, 0xC3, 0xA9); // "café"
    const out = _decodeOFXBuffer(buf(...bytes));
    expect(out).toContain('café');
  });

  it('OFX sem header válido cai no fallback windows-1252', () => {
    // "ção" em Latin-1 — sem header
    const out = _decodeOFXBuffer(buf(0xE7, 0xE3, 0x6F));
    expect(out).toBe('ção');
  });
});
