# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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
