<div align="center">

<img src="https://github.com/euguilouren.png?size=120" width="90" style="border-radius:50%" alt="Luan Guilherme Lourenço">

# FluxoPRO

**Dashboard financeiro 100% no navegador**

[![CI](https://github.com/euguilouren/FluxoPRO/actions/workflows/ci.yml/badge.svg)](https://github.com/euguilouren/FluxoPRO/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Testes](https://img.shields.io/badge/testes-391%20Python%20%2B%2098%20JS-2e7d32)
![Anti-Fraude](https://img.shields.io/badge/anti--fraude-8%20algoritmos-C9A84C)
![License](https://img.shields.io/badge/licença-MIT-22c55e)

**Criado por [Luan Guilherme Lourenço](https://github.com/euguilouren)**

[![GitHub](https://img.shields.io/badge/GitHub-euguilouren-181717?logo=github&logoColor=white)](https://github.com/euguilouren)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-euguilouren-0A66C2?logo=linkedin&logoColor=white)](https://linkedin.com/in/euguilouren)

**[🚀 Abrir dashboard online →](https://euguilouren.github.io/FluxoPRO/)**

</div>

---

## Sobre o Desenvolvedor

**Luan Guilherme Lourenço** é desenvolvedor especializado em automação financeira e soluções de dados para empresas brasileiras. Criou o FluxoPRO para democratizar análises financeiras profissionais — o que antes exigia horas de trabalho em consultoria, agora acontece em segundos, direto no navegador.

- **GitHub:** [github.com/euguilouren](https://github.com/euguilouren)
- **LinkedIn:** [linkedin.com/in/euguilouren](https://linkedin.com/in/euguilouren)

---

## O que faz

Arraste qualquer planilha `.xlsx` ou `.csv` e obtenha instantaneamente:

| Análise | O que entrega |
|---------|--------------|
| **KPIs financeiros** | Receitas, despesas, resultado líquido, ticket médio |
| **Auditoria** | Duplicatas, outliers, campos vazios, inconsistências temporais |
| **Aging / Recebíveis** | Faixas de vencimento com gráfico visual |
| **DRE automático** | Receitas, CMV e despesas classificados (padrão CPC 26) |
| **Pareto (curva ABC)** | Clientes/fornecedores que geram 80% do resultado |
| **Anti-Fraude** | 8 algoritmos: Lei de Benford, duplicatas (exatas + fuzzy), fracionamento e mais |
| **Detecção de ERP** | Mapeamento automático de colunas de 20 sistemas brasileiros |

### Sistema Anti-Fraude (8 algoritmos)

Implementação em paridade entre o dashboard web (JS, `calcularAntiFraude` em `index.html`) e o módulo Python (`fraude_detector.py`).

| Algoritmo | Detecta |
|-----------|---------|
| Lei de Benford | Distribuição anômala de primeiros dígitos (chi-quadrado) |
| Duplicatas Exatas | Mesma chave/valor/data — registros idênticos |
| Duplicatas Fuzzy | Mesmo valor ±1% + mesma entidade + data ±30 dias |
| Números Redondos | Concentração suspeita de valores redondos (>15%) |
| Fracionamento | Transações fracionadas abaixo de limites em janela de 30 dias |
| Anomalias Temporais | Transações em fins de semana e feriados nacionais |
| Outliers por Entidade | Z-score por fornecedor/cliente (σ ≥ 3) |
| Concentração | Entidade com >30% do volume total |

> O score consolidado (CRÍTICO / ALTO / MÉDIO / BAIXO / LIMPO) é gerado a partir dos algoritmos acima.

---

## ERPs Suportados (20)

TOTVS Protheus · TOTVS RM · TOTVS Datasul · Omie · Questor · SAP B1 · Domínio · Sankhya · Senior · Cigam · Alterdata · Linx · Mega · Nibo · Granatum · Conta Azul · Bling · Tiny · GestãoClick · NFe XML

---

## Modos de Uso

| Modo | Arquivo | Descrição |
|------|---------|-----------|
| Dashboard web | `index.html` | Abre no navegador — sem servidor, sem Python |
| CLI interativo | `rodar.py` | Processa arquivo e gera Excel + briefing |
| Monitor autônomo | `motor_automatico.py` | Daemon que monitora pasta continuamente |
| Detecção de fraudes | `fraude_detector.py` | Módulo Python independente |

---

## Instalação

```bash
git clone https://github.com/euguilouren/FluxoPRO
cd FluxoPRO
pip install -r requirements.txt
```

**No Windows:**
```
instalar.bat   # instala dependências
abrir.bat      # abre o dashboard no navegador
```

### Dashboard (sem Python)

Abra `index.html` diretamente no Chrome, Edge ou Firefox. Arraste uma planilha `.xlsx` ou `.csv` e pronto.

### CLI

```bash
python rodar.py
# Gera resultado.xlsx e briefing.txt na mesma pasta
```

### Monitor Autônomo

```bash
python motor_automatico.py              # monitora pasta_entrada/ continuamente
python motor_automatico.py --once       # processa uma vez e sai
python motor_automatico.py --arquivo minha.xlsx
```

### Detecção de Fraudes (Python)

```python
from fraude_detector import FraudeDetector
import pandas as pd

df = pd.read_excel("lancamentos.xlsx")
resultado = FraudeDetector.analisar(df, col_valor="Valor", col_entidade="Cliente", col_data="Data")

print(f"Score: {resultado['score']} — {resultado['nivel']}")
print(f"Alertas: {resultado['alertas']}")
```

---

## Testes

```bash
pip install -r requirements-dev.txt
pytest tests/ -v              # Python: 391 testes
npm ci && npm run test:js     # JavaScript: 160 testes (Vitest)
```

---

## Setup local (opcional)

Instale o git hook de pré-commit para validar `index.html` antes de cada commit
(DOCTYPE, branding, Service Worker registrado, `console.log`, `Chart.destroy`
antes de `new Chart`, e mais):

```bash
bash scripts/install-hooks.sh
```

Para desinstalar: `rm .git/hooks/pre-commit`.

---

## Segurança

- **CSP** (`Content-Security-Policy`) restringindo scripts, frames e conexões externas
- **Bandit SAST** em cada push — zero findings medium/high
- **Verificação de integridade dos CDNs** (SHA-384) a cada run de CI
- **Anti-fraude** com 8 algoritmos de detecção no frontend e backend

---

## Pipeline de Deploy

```
push → main
  └─► .github/workflows/deploy.yml
        → scripts/obfuscar_html.py (obfusca JS)
        → GitHub Pages → euguilouren.github.io/FluxoPRO/
```

---

## Licença

MIT © [Luan Guilherme Lourenço](https://github.com/euguilouren)
