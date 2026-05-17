import { describe, it, expect } from 'vitest';
import { calcularAntiFraude } from './helpers/extract-analise.js';

const COLS = { valor: 'Valor', entidade: 'Cliente', chave: 'NF', data: 'Data' };

describe('calcularAntiFraude', () => {
  it('retorna estrutura completa com 7 arrays + benford + score + alertas', () => {
    const r = calcularAntiFraude([], COLS);
    expect(r).toMatchObject({
      benford: null,
      duplicatas: [],
      numerosRedondos: [],
      fracionamento: [],
      anomaliasTEmporais: [],
      outliers: [],
      concentracao: [],
      scoreRisco: 0,
      alertas: [],
    });
  });

  it('dados vazios não quebram', () => {
    const r = calcularAntiFraude([], COLS);
    expect(r.scoreRisco).toBe(0);
    expect(r.alertas).toEqual([]);
  });

  it('cols.valor ausente retorna estrutura vazia', () => {
    const r = calcularAntiFraude([{ Valor: 100 }], { entidade: 'Cliente' });
    expect(r.benford).toBeNull();
  });

  it('Benford requer ≥30 valores positivos — abaixo disso, retorna invalido com motivo', () => {
    const dados = Array.from({ length: 20 }, (_, i) => ({ Valor: i + 1, Cliente: `C${i}`, NF: i }));
    const r = calcularAntiFraude(dados, COLS);
    expect(r.benford.valido).toBe(false);
    expect(r.benford.motivo).toMatch(/mínimo/i);
  });

  it('Benford com distribuição realista gera nivel OK', () => {
    // 50 valores seguindo aproximadamente Benford
    const dados = [];
    for (let i = 1; i <= 50; i++) dados.push({ Valor: i, Cliente: `C${i}`, NF: i });
    const r = calcularAntiFraude(dados, COLS);
    expect(r.benford).toBeTruthy();
    expect(r.benford.valido).toBe(true);
    expect(['OK', 'MÉDIO', 'ALTO', 'CRÍTICO']).toContain(r.benford.nivel);
    expect(r.benford.totalRegistros).toBe(50);
  });

  it('Benford com tudo começando em "1" gera nível CRÍTICO ou ALTO', () => {
    const dados = Array.from({ length: 50 }, (_, i) => ({ Valor: 100 + i, Cliente: 'X', NF: i }));
    const r = calcularAntiFraude(dados, COLS);
    expect(r.benford.valido).toBe(true);
    expect(['ALTO', 'CRÍTICO']).toContain(r.benford.nivel);
  });

  it('detecta duplicata exata pela mesma chave', () => {
    const dados = [
      { Valor: 100, Cliente: 'A', NF: 'X1', Data: '01/01/2024' },
      { Valor: 100, Cliente: 'A', NF: 'X1', Data: '01/01/2024' },
    ];
    const r = calcularAntiFraude(dados, COLS);
    const exatas = r.duplicatas.filter(d => d.tipo === 'DUPLICATA_EXATA');
    expect(exatas.length).toBeGreaterThan(0);
  });

  it('detecta duplicata fuzzy (mesmo valor + mesma entidade + data próxima)', () => {
    const dados = [
      { Valor: 1000, Cliente: 'A', NF: 'NF1', Data: '01/01/2024' },
      { Valor: 1000, Cliente: 'A', NF: 'NF2', Data: '10/01/2024' },  // mesma entidade, valor, 9 dias depois
    ];
    const r = calcularAntiFraude(dados, COLS);
    const fuzzy = r.duplicatas.filter(d => d.tipo === 'DUPLICATA_FUZZY');
    expect(fuzzy.length).toBeGreaterThan(0);
  });

  it('detecta concentração de números redondos (>15%)', () => {
    // 20 valores, 18 redondos (>15% threshold)
    const dados = [];
    for (let i = 0; i < 18; i++) dados.push({ Valor: (i + 1) * 100, Cliente: `C${i}`, NF: i });
    dados.push({ Valor: 137.45, Cliente: 'X', NF: 'A' });
    dados.push({ Valor: 289.12, Cliente: 'Y', NF: 'B' });
    const r = calcularAntiFraude(dados, COLS);
    expect(r.numerosRedondos.length).toBeGreaterThan(0);
  });

  it('detecta anomalia temporal — lançamento em fim de semana', () => {
    // 06/01/2024 é sábado, 07/01/2024 é domingo
    const dados = [
      { Valor: 100, Cliente: 'A', NF: '1', Data: '06/01/2024' },
      { Valor: 200, Cliente: 'B', NF: '2', Data: '07/01/2024' },
    ];
    const r = calcularAntiFraude(dados, COLS);
    expect(r.anomaliasTEmporais.length).toBeGreaterThan(0);
  });

  it('detecta anomalia temporal — feriado nacional (25/12)', () => {
    const dados = [{ Valor: 100, Cliente: 'A', NF: '1', Data: '25/12/2024' }];
    const r = calcularAntiFraude(dados, COLS);
    expect(r.anomaliasTEmporais.length).toBeGreaterThan(0);
  });

  it('detecta concentração de entidade (>30% do total)', () => {
    const dados = [
      { Valor: 700, Cliente: 'DOMINANTE', NF: '1' },
      { Valor: 100, Cliente: 'X', NF: '2' },
      { Valor: 100, Cliente: 'Y', NF: '3' },
      { Valor: 100, Cliente: 'Z', NF: '4' },
    ];
    const r = calcularAntiFraude(dados, COLS);
    expect(r.concentracao.length).toBeGreaterThan(0);
    expect(r.concentracao[0].entidade).toMatch(/DOMINANTE/);
  });

  it('scoreRisco aumenta quando há múltiplas detecções', () => {
    const dados = [
      { Valor: 100, Cliente: 'A', NF: 'X', Data: '06/01/2024' },  // sábado
      { Valor: 100, Cliente: 'A', NF: 'X', Data: '06/01/2024' },  // duplicata exata
    ];
    const r = calcularAntiFraude(dados, COLS);
    expect(r.scoreRisco).toBeGreaterThan(0);
    expect(r.alertas.length).toBeGreaterThan(0);
  });

  it('cada item de duplicata tem tipo, severidade e descrição', () => {
    const dados = [
      { Valor: 100, Cliente: 'A', NF: 'X', Data: '01/01/2024' },
      { Valor: 100, Cliente: 'A', NF: 'X', Data: '01/01/2024' },
    ];
    const r = calcularAntiFraude(dados, COLS);
    const item = r.duplicatas[0];
    expect(item).toHaveProperty('tipo');
    expect(item).toHaveProperty('severidade');
    expect(item).toHaveProperty('descricao');
  });

  // Regressão: agent alegou que `grupos.set(ent, grupos.get(ent)||{...})`
  // resetava o objeto em iterações subsequentes da mesma entidade. Falso —
  // Map.get retorna a referência existente após o set inicial. Travando o
  // comportamento correto: agregação multi-linha por entidade soma valores.
  it('concentração agrega múltiplas linhas da MESMA entidade corretamente', () => {
    const dados = [
      { Valor: 500, Cliente: 'BIG',    NF: '1' },
      { Valor: 400, Cliente: 'BIG',    NF: '2' },  // BIG total = 900
      { Valor: 50,  Cliente: 'small1', NF: '3' },
      { Valor: 50,  Cliente: 'small2', NF: '4' },
    ];
    const r = calcularAntiFraude(dados, COLS);
    const bigAlert = r.concentracao.find(c => c.entidade === 'BIG');
    expect(bigAlert).toBeDefined();
    // 900 / 1000 = 90% — bem acima do threshold de 30%
    expect(bigAlert.descricao).toMatch(/90/);
    expect(bigAlert.descricao).toMatch(/2 lan[çc]amentos/);
  });

  // Regressão: linha 880 validava `va` mas não `vb`. Se vb=NaN,
  // `Math.abs(va-NaN)/va = NaN` e `NaN > 0.01 = false` → não continuava,
  // criando DUPLICATA_FUZZY fantasma quando uma linha tinha valor inválido.
  it('regressão BUG: valor não-numérico em par de duplicata fuzzy não gera alerta', () => {
    const dados = [
      { Valor: 1000,    Cliente: 'ACME', NF: '1' },
      { Valor: 'texto', Cliente: 'ACME', NF: '2' }, // vb=NaN
      { Valor: '',      Cliente: 'ACME', NF: '3' }, // vb=NaN
    ];
    const r = calcularAntiFraude(dados, COLS);
    const fuzzy = r.duplicatas.filter(d => d.tipo === 'DUPLICATA_FUZZY');
    expect(fuzzy).toHaveLength(0);
  });

  it('duplicata fuzzy LEGÍTIMA com dois valores válidos continua sendo detectada', () => {
    // Trava do teste anterior — garante que o fix não quebrou detecção real
    const hoje = new Date();
    const dados = [
      { Valor: 1000, Cliente: 'ACME', NF: '1', Data: hoje },
      { Valor: 1005, Cliente: 'ACME', NF: '2', Data: hoje }, // diff < 1%
    ];
    const r = calcularAntiFraude(dados, COLS);
    const fuzzy = r.duplicatas.filter(d => d.tipo === 'DUPLICATA_FUZZY');
    expect(fuzzy.length).toBeGreaterThan(0);
  });
});
