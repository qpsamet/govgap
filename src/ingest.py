"""Multi-format document ingestion.

Normalises any supported input to clean text so the rest of the pipeline only
ever sees a string. Supported inputs: a URL, a PDF, a DOCX, a text/markdown/HTML
file, or raw pasted text. Format handling lives here, deterministically, rather
than as an LLM tool decision.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import requests
from bs4 import BeautifulSoup

MAX_CHARS = 60_000

ACCEPTED_FORMATS = (
    "a URL (https://...), or a file (.pdf, .docx, .txt, .md, .html)"
)


@dataclass
class IngestResult:
    text: str
    label: str   # human-readable source label (filename or URL)
    kind: str    # url | pdf | docx | text | markdown | html


class IngestError(Exception):
    """Input could not be read, or the format is unsupported."""


def _clean(text: str) -> str:
    lines = [ln.rstrip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln.strip())[:MAX_CHARS]


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    return soup.get_text(separator="\n")


def from_url(url: str) -> IngestResult:
    try:
        resp = requests.get(url, timeout=30, headers={"User-Agent": "govgap-agent"})
        resp.raise_for_status()
    except requests.RequestException as e:
        raise IngestError(f"Could not fetch the URL: {e}") from e
    text = _clean(_html_to_text(resp.text))
    if len(text) < 200:
        raise IngestError(
            "The page returned very little text, which usually means it is "
            "rendered by JavaScript. Save it as a PDF or paste the text instead."
        )
    return IngestResult(text=text, label=url, kind="url")


def from_pdf(path: Path) -> IngestResult:
    try:
        import pdfplumber
    except ImportError as e:
        raise IngestError("PDF support needs 'pdfplumber' (pip install pdfplumber).") from e
    parts: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    text = _clean("\n".join(parts))
    if not text:
        raise IngestError(
            "No selectable text found in the PDF (it may be a scanned image). "
            "OCR is not supported; paste the text instead."
        )
    return IngestResult(text=text, label=path.name, kind="pdf")


def from_docx(path: Path) -> IngestResult:
    try:
        import docx
    except ImportError as e:
        raise IngestError("DOCX support needs 'python-docx' (pip install python-docx).") from e
    document = docx.Document(str(path))
    parts = [p.text for p in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            parts.append(" | ".join(cell.text for cell in row.cells))
    text = _clean("\n".join(parts))
    if not text:
        raise IngestError("The .docx file contained no readable text.")
    return IngestResult(text=text, label=path.name, kind="docx")


def from_textfile(path: Path) -> IngestResult:
    raw = path.read_text(encoding="utf-8", errors="replace")
    ext = path.suffix.lower()
    if ext in (".html", ".htm"):
        return IngestResult(text=_clean(_html_to_text(raw)), label=path.name, kind="html")
    kind = "markdown" if ext in (".md", ".markdown") else "text"
    return IngestResult(text=_clean(raw), label=path.name, kind=kind)


def load_document(source: str) -> IngestResult:
    """Normalise any supported input to clean text.

    A string that starts with http(s) is fetched as a URL; anything else is
    treated as a file path and dispatched by extension.
    """
    if source.startswith(("http://", "https://")):
        return from_url(source)

    path = Path(source).expanduser()
    if not path.exists():
        raise IngestError(f"No file found at '{source}'. Provide {ACCEPTED_FORMATS}.")

    ext = path.suffix.lower()
    if ext == ".pdf":
        return from_pdf(path)
    if ext == ".docx":
        return from_docx(path)
    if ext in (".txt", ".md", ".markdown", ".html", ".htm"):
        return from_textfile(path)
    raise IngestError(
        f"Unsupported file type '{ext or 'unknown'}'. Accepted: {ACCEPTED_FORMATS}."
    )
