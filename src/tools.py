import requests
from bs4 import BeautifulSoup
from pathlib import Path

MAX_CHARS = 60000  # safe truncation budget


def fetch_document_impl(source: str) -> str:
    """Read a local snapshot file, or fetch a URL and strip it to clean text."""
    if source.startswith(("http://", "https://")):
        resp = requests.get(source, timeout=30, headers={"User-Agent": "govgap-agent"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
    else:
        text = Path(source).read_text(encoding="utf-8")
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)[:MAX_CHARS]
