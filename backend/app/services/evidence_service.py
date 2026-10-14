"""Evidence document extraction for chronology analysis."""

import io
from functools import lru_cache
from pathlib import Path

from docx import Document

from app.config.settings import settings


class EvidenceExtractionError(ValueError):
    """Raised when an evidence file cannot be extracted."""


@lru_cache(maxsize=1)
def _get_paddle_ocr():
    try:
        from paddleocr import PaddleOCR
    except ImportError as error:
        raise EvidenceExtractionError(
            "Scanned-PDF OCR requires PaddleOCR. Install backend requirements and restart the server."
        ) from error

    try:
        try:
            return PaddleOCR(lang="en")
        except TypeError:
            return PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
    except Exception as error:
        raise EvidenceExtractionError(f"Unable to initialize PaddleOCR: {error}") from error


def _extract_scanned_pdf_text(content: bytes) -> str:
    try:
        import fitz
    except ImportError as error:
        raise EvidenceExtractionError("PDF extraction requires PyMuPDF.") from error

    try:
        import numpy as np
    except ImportError as error:
        raise EvidenceExtractionError("Scanned-PDF OCR requires NumPy.") from error

    ocr = _get_paddle_ocr()
    lines = []
    with fitz.open(stream=content, filetype="pdf") as document:
        page_limit = max(1, settings.OCR_MAX_PAGES)
        for page in list(document)[:page_limit]:
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
                pixmap.height, pixmap.width, pixmap.n
            )
            try:
                result = ocr.ocr(image, cls=True)
            except AttributeError:
                result = ocr.predict(image)

            if not result:
                continue
            page_result = result[0] if isinstance(result, list) else result
            if isinstance(page_result, list):
                for item in page_result:
                    if len(item) > 1 and item[1]:
                        lines.append(str(item[1][0]))
            elif hasattr(page_result, "json"):
                payload = page_result.json
                if callable(payload):
                    payload = payload()
                if isinstance(payload, str):
                    import json
                    payload = json.loads(payload)
                for text in payload.get("rec_texts", []):
                    if text:
                        lines.append(str(text))
    return "\n".join(lines).strip()


def extract_evidence_text(filename: str, content: bytes) -> tuple[str, str]:
    suffix = Path(filename or "").suffix.lower()
    if suffix in {".txt", ".md"}:
        return content.decode("utf-8", errors="replace").strip(), "plain_text"
    if suffix == ".docx":
        document = Document(io.BytesIO(content))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs).strip()
        return text, "docx_text"
    if suffix == ".pdf":
        try:
            import fitz
        except ImportError as error:
            raise EvidenceExtractionError("PDF extraction requires PyMuPDF.") from error
        pages = []
        with fitz.open(stream=content, filetype="pdf") as document:
            for page in document:
                pages.append(page.get_text("text"))
        text = "\n".join(pages).strip()
        if not text:
            if settings.OCR_PROVIDER.lower() != "paddleocr":
                raise EvidenceExtractionError(
                    "The PDF contains no extractable text. Set OCR_PROVIDER=paddleocr for scanned-PDF processing."
                )
            text = _extract_scanned_pdf_text(content)
            if not text:
                raise EvidenceExtractionError("PaddleOCR could not extract text from the scanned PDF.")
            return text, "pdf_paddleocr"
        return text, "pdf_text"
    raise EvidenceExtractionError("Supported evidence formats are PDF, DOCX, TXT, and MD.")
