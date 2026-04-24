"""
Exportador PDF — converte relatório HTML para PDF.

Tenta usar weasyprint (produção). Se não disponível, cai para
fallback baseado em pdfkit/wkhtmltopdf ou levanta ImportError
com instrução clara.

Uso:
    pdf_bytes = ExportadorPDF.gerar(html_str)
    Path("relatorio.pdf").write_bytes(pdf_bytes)
"""
from __future__ import annotations

import importlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ExportadorPDF:
    """Converte HTML em bytes PDF."""

    @staticmethod
    def gerar(html: str, base_url: Optional[str] = None) -> bytes:
        """
        Converte *html* para PDF.

        Tenta weasyprint primeiro; fallback para pdfkit.
        Levanta RuntimeError se nenhum backend disponível.
        """
        for backend in (_tentar_weasyprint, _tentar_pdfkit):
            resultado = backend(html, base_url)
            if resultado is not None:
                return resultado
        raise RuntimeError(
            "Nenhum backend PDF disponível. Instale weasyprint ou wkhtmltopdf:\n"
            "  pip install weasyprint\n"
            "  # ou: apt-get install wkhtmltopdf && pip install pdfkit"
        )

    @staticmethod
    def disponivel() -> bool:
        """Retorna True se pelo menos um backend PDF estiver disponível."""
        return (
            importlib.util.find_spec("weasyprint") is not None
            or importlib.util.find_spec("pdfkit") is not None
        )


def _tentar_weasyprint(html: str, base_url: Optional[str]) -> Optional[bytes]:
    try:
        import weasyprint  # noqa: PLC0415
        documento = weasyprint.HTML(string=html, base_url=base_url)
        return documento.write_pdf()
    except ImportError:
        return None
    except Exception as exc:
        logger.warning("weasyprint falhou: %s — tentando fallback", exc)
        return None


def _tentar_pdfkit(html: str, _base_url: Optional[str]) -> Optional[bytes]:
    try:
        import pdfkit  # noqa: PLC0415
        import tempfile, os

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            pdfkit.from_string(html, tmp_path, options={"quiet": ""})
            return open(tmp_path, "rb").read()
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    except ImportError:
        return None
    except Exception as exc:
        logger.warning("pdfkit falhou: %s", exc)
        return None
