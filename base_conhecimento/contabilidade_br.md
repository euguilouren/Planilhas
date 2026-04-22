# Contabilidade Brasileira — Referência para Análise Financeira

## 1. ESTRUTURA DO DRE (CPC 26 / Lei 6.404)

```
(+) Receita Bruta de Vendas e Serviços
(-) Deduções da Receita Bruta
    • ICMS sobre vendas
    • PIS / COFINS
    • ISS (serviços)
    • IPI (indústria)
    • Devoluções e abatimentos
(=) RECEITA LÍQUIDA

(-) Custo dos Produtos Vendidos (CPV) / CMV / CSV
(=) LUCRO BRUTO

(-) Despesas Operacionais
    • Despesas com Vendas (comissões, marketing, frete)
    • Despesas Administrativas (salários admin, aluguel, TI)
    • Outras despesas operacionais
(=) RESULTADO OPERACIONAL (EBIT)

(+/-) Resultado Financeiro
    • Receitas financeiras (juros ativos, aplicações)
    • Despesas financeiras (juros passivos, IOF, variação cambial)
(=) RESULTADO ANTES DO IR/CSLL (LAIR)

(-) Imposto de Renda (IRPJ)
(-) Contribuição Social sobre o Lucro (CSLL)
(=) LUCRO/PREJUÍZO LÍQUIDO DO EXERCÍCIO
```

## 2. IMPOSTOS SOBRE RECEITA (Dedução)

| Imposto | Base | Alíquota padrão | Posição no DRE |
|---------|------|-----------------|----------------|
| ICMS | Receita bruta | 7–18% (varia por UF) | Dedução |
| PIS | Receita bruta | 0,65% (cumulativo) / 1,65% (não-cumulativo) | Dedução |
| COFINS | Receita bruta | 3% (cumulativo) / 7,6% (não-cumulativo) | Dedução |
| ISS | Prestação de serviços | 2–5% (varia por município) | Dedução |
| IPI | Saída de produtos industrializados | Variável por NCM | Dedução |

## 3. ENCARGOS SOBRE FOLHA (Despesa Operacional)

| Encargo | % sobre salário bruto |
|---------|-----------------------|
| INSS Patronal | 20% |
| FGTS | 8% |
| RAT / SAT | 1–3% (conforme CNAE) |
| Terceiros (SESI, SENAI...) | ~5,8% |
| **Total aproximado** | **~35%** |

## 4. REGIMES TRIBUTÁRIOS

### Simples Nacional
- Faixas de 6% a 33% sobre receita bruta
- Unifica: IRPJ, CSLL, PIS, COFINS, INSS Patronal, IPI, ICMS, ISS
- Limite: R$ 4,8 milhões/ano

### Lucro Presumido
- IRPJ: 15% + adicional 10% acima R$ 20k/mês
- CSLL: 9%
- Base presumida: 8% (comércio/indústria), 32% (serviços), 16% (transporte)
- PIS: 0,65% | COFINS: 3% (cumulativo)

### Lucro Real
- IRPJ/CSLL sobre lucro efetivo
- PIS: 1,65% | COFINS: 7,6% (não-cumulativo, com créditos)
- Obrigatório para receita > R$ 78 milhões/ano ou setores específicos

## 5. INDICADORES DE SAÚDE FINANCEIRA — REFERÊNCIAS BR

| Indicador | Fórmula | Referência | Alerta |
|-----------|---------|------------|--------|
| Liquidez Corrente | AC / PC | > 1,0 | < 0,8 |
| Liquidez Seca | (AC - Estoques) / PC | > 0,8 | < 0,5 |
| Liquidez Imediata | Caixa / PC | > 0,3 | < 0,1 |
| Margem Bruta | Lucro Bruto / Rec. Líq. | > 30% | < 15% |
| Margem EBIT | EBIT / Rec. Líq. | > 10% | < 5% |
| Margem Líquida | Lucro Líq. / Rec. Líq. | > 5% | < 0% |
| ROE | Lucro Líq. / PL | > 15% | < 5% |
| Endividamento | Dívida Total / PL | < 100% | > 200% |
| Prazo Médio Receb. | (CR / Receita) × 30 | < 30 dias | > 60 dias |
| Prazo Médio Pagam. | (CP / CPV) × 30 | > 30 dias | < 15 dias |
| Giro do Ativo | Receita / Ativo Total | > 1,0 | < 0,5 |

## 6. PLANO DE CONTAS RESUMIDO (NBC TG 1000)

### ATIVO
- **Circulante**: Caixa, Bancos, Aplicações, Clientes, Estoques, Adiantamentos
- **Não Circulante**: Realizável LP, Investimentos, Imobilizado, Intangível

### PASSIVO
- **Circulante**: Fornecedores, Salários a pagar, Impostos a recolher, Empréstimos CP
- **Não Circulante**: Financiamentos LP, Debêntures, Provisões LP
- **PL**: Capital Social, Reservas, Lucros/Prejuízos Acumulados

## 7. CONCILIAÇÃO BANCÁRIA — ITENS FREQUENTES

| Tipo | Descrição | Ação |
|------|-----------|------|
| Depósito em trânsito | Registrado no sistema, não no banco ainda | Aguardar compensação |
| Cheque não compensado | Emitido, não debitado pelo banco | Monitorar validade (6 meses) |
| Tarifas bancárias | No extrato, não registrado | Lançar no sistema |
| Estorno | Crédito/débito inesperado | Investigar origem |
| DOC/TED em trânsito | D+1 útil | Aguardar |

## 8. AGING — CLASSIFICAÇÃO E PROVISÃO SUGERIDA

| Faixa | Dias de atraso | Provisão PCLD sugerida |
|-------|---------------|------------------------|
| A vencer | — | 0% |
| Vencido recente | 1–30 | 5% |
| Vencido | 31–60 | 15% |
| Vencido | 61–90 | 30% |
| Vencido grave | 91–180 | 50% |
| Vencido crítico | +180 | 100% |

## 9. ALERTAS AUTOMÁTICOS RECOMENDADOS

- Receita negativa → provável estorno não tratado
- CMV > Receita Bruta → margem bruta negativa (revisar custo ou preço)
- Despesa financeira > 5% da receita → alerta de endividamento
- Aging +90 dias > 20% da carteira → risco de liquidez
- Duplicatas com mesmo valor + data próxima (±3 dias) → possível duplicidade

## 10. NOTAS FISCAIS — CAMPOS PADRÃO SPED/XML

| Campo XML | Descrição | Uso na análise |
|-----------|-----------|----------------|
| nNF | Número da NF | Chave para conciliação |
| dhEmi | Data de emissão | Col de data principal |
| vNF | Valor total da NF | Col de valor |
| CNPJ (emit/dest) | CNPJ emitente/destinatário | Entidade |
| natOp | Natureza da operação | Categoria/tipo |
| vICMS, vPIS, vCOFINS | Impostos destacados | Deduções |
