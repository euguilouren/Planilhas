# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [1.3.0] — 2026-04-26

### Added
- **CLAUDE.md** — architecture guide for AI-assisted refinements: file map, state variables,
  CSS variables, extension points, ERP how-to, and protected sections.
- **ERP auto-detection in JS** — `MAPAS_ERP_JS` object covers 20 Brazilian ERPs;
  `detectarERP()` identifies system from column headers; toast notification on match.
- **ERP selector** — `<select id="sel-erp-sistema">` in the toolbar lets users force a
  specific ERP mapping; hidden on mobile (≤600 px).
- **Redesigned drop zone** — SVG icon, upload title/subtitle, 3-step workflow hint,
  `.btn-upload-choose` primary button, `drag-over` visual state.
- **Integrity verification card** — `#card-verificacao` with cross-checks (record count,
  Pareto consistency, DRE consistency, date validity, null values); each check shows
  a "Como investigar:" guidance block when flagged.
- **Sign-based DRE** — when no `Categoria` column is present, `construirDRE()` classifies
  positive values as Receita and negative as Despesas automatically; a blue banner signals
  the `(+)/(-) mode` to the user.
- **Downloadable template** — `baixarTemplate()` generates a 2-sheet XLSX: `DADOS` with
  sample rows (positive/negative values) and `INSTRUÇÕES` with column documentation.
- **20 ERPs in Python** — `base_conhecimento/__init__.py` expanded from 4 to 20 systems
  including TOTVS RM/Datasul, Domínio, Sankhya, Sênior, Conta Azul, Bling, Tiny, Nibo,
  Granatum, Cigam, Linx, Alterdata, Mega, GestãoClick, NFe XML.
- **Markdown rendering** — Claude API responses now rendered as formatted HTML
  (headings, bold, lists, tables) instead of plain text.

### Changed
- **Claude model** updated from `claude-opus-4-5` to `claude-opus-4-7`.
- **`max_tokens`** raised from 1024 to 2048 to prevent analysis truncation.
- **Categoria field removed from column-mapping UI** — auto-detected silently from ERP
  mapping or sign; `_cols` reduced to 5 keys.
- **Pareto consistency check** now shows INFO (not DIVERGENTE) when top-15 is a subset
  of more than 15 entities — false alarm eliminated.
- **All integrity warnings** include an actionable "Como investigar:" section.
- **API key disclosure** corrected: tooltip now says "salva apenas neste navegador
  (localStorage)" instead of "nunca é armazenada".

### Fixed
- `javascript-obfuscator` CLI flags `--domain-lock` and `--string-array-encoding` were
  passed as JSON arrays (`["base64"]`) — corrected to plain strings (`base64`).
- `_gerarBriefing()` aging loop used `Object.entries()` on an array and wrong field names
  (`a.sev`, `a.msg`) — fixed to `.filter().forEach()` with `a.severidade`/`a.descricao`.
- `_ultimoDre` accessed as array after `construirDRE()` changed to return `{linhas, modo}`
  object — all references updated.
- `package.json` and `scripts/obfuscar_html.py` referenced deleted `src/index.html` after
  the source file was moved back to root — corrected.

### Security
- `numpy` upgraded 1.26.4 → 2.2.6 (CVE mitigations).
- `PyYAML` upgraded 6.0.1 → 6.0.3.
- `pytest` upgraded 8.3.5 → 9.0.3 (CVE-2025-71176).

---

## [1.2.0] — 2026-04-23

### Added
- **Path traversal protection** — `ProcessadorArquivo._validar_caminho_arquivo()` resolves
  paths with `Path.resolve()` and blocks symlinks escaping `pasta_entrada`.
- **Email retry with exponential backoff** — `_enviar_email()` retries SMTP up to 3 times
  with 2 s → 4 s → 8 s delays on transient failures.
- **ERP fuzzy matching** — `_normalizar_colunas()` uses `difflib.get_close_matches` (cutoff
  0.85) to detect ERP column names even with minor typos or accents.
- **Versioning** — `__version__` and `__author__` constants in `toolkit_financeiro.py`.
- **CHANGELOG.md** — this file.
- **ARIA accessibility** — `role`, `aria-label`, `aria-live` attributes throughout the
  generated HTML report.
- **Optional PDF export** — `GeradorHTML.gerar_pdf()` wraps WeasyPrint; silently skips if
  the library is not installed.
- **`toolkit/` package** — `toolkit_financeiro.py` split into focused submodules
  (`_status`, `_leitor`, `_auditor`, `_analista`, `_montador`, `_verificador`);
  original module kept as a backward-compatible re-export shim.
- **Google-style docstrings** — added to all public API methods.
- **Integration tests** — `tests/test_integration.py` exercises the full CSV → HTML → Excel
  pipeline end-to-end.
- **Docker support** — `Dockerfile`, `docker-compose.yml`, and
  `systemd/toolkit-financeiro.service` for containerised / daemon deployment.

### Changed
- `_normalizar_colunas()` now uses a list (ordered) instead of a set for `sinais` fields.
- `validar_config()` validates email address format with a regex.
- SMTP credential fallback emits `logger.warning` instead of silently using config value.

### Fixed
- `IndexError` when `dados` dict is empty after reading — now raises `ValueError` with a
  clear message.
- `smtplib.SMTP` called without `timeout` could hang indefinitely — now uses `timeout=10`.
- `print()` calls in `--arquivo` mode replaced with `logger.info()`.
- Removed unused `import shutil` and `import numpy as np` in `relatorio_html.py`.

---

## [1.1.0] — 2026-04-22

### Added
- **XSS prevention** — all user-supplied strings in generated HTML are escaped via
  `html.escape()` through the `GeradorHTML._esc()` helper.
- **Luxury UI** — Inter font, navy/gold palette, KPI cards, pill badges, step indicator and
  improved drop zone in `index.html`.
- **9-token colour system** — `config.yaml` `tema` section expanded with `cor_dark`,
  `cor_ok_text`, `cor_alerta_text`, `cor_critico_text`.
- **XSS tests** — five security-focused test cases in `tests/test_relatorio_html.py`.
- **Motor tests** — `tests/test_motor_automatico.py` covering SMTP, credential warnings and
  file processing edge cases.
- **Email format validation** — `validar_config()` rejects malformed addresses in
  `destinatarios`.

### Fixed
- Silent credential exposure when `EMAIL_SENHA` env var is missing — now emits warning.
- Empty destinatários list with email active no longer silently passes.

---

## [1.0.0] — 2026-04-20

### Added
- Initial release: `toolkit_financeiro.py`, `motor_automatico.py`, `relatorio_html.py`,
  `index.html`, `config.yaml`.
- Autonomous folder watcher (`motor_automatico.py`).
- HTML report generation with aging, DRE, Pareto sections.
- Excel output with formatted worksheets via `MontadorPlanilha`.
- Unit tests in `tests/`.
