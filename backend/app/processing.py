import csv
import io
import re
from pathlib import Path

import httpx
from docx import Document as DocxDocument
from pypdf import PdfReader

from .config import settings


def extract_text(path: Path, content_type: str, filename: str) -> str:
    if content_type == "text/csv" or filename.lower().endswith(".csv"):
        return path.read_text(encoding="utf-8-sig", errors="replace")

    if content_type.startswith("text/") or filename.lower().endswith(".txt"):
        return path.read_text(encoding="utf-8-sig", errors="replace")

    if filename.lower().endswith(".docx") or content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        document = DocxDocument(path)
        return "\n".join(paragraph.text for paragraph in document.paragraphs)

    if filename.lower().endswith(".pdf") or content_type == "application/pdf":
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    try:
        response = httpx.post(
            settings.tika_url + "/tika",
            content=path.read_bytes(),
            headers={"Accept": "text/plain", "Content-Type": content_type},
            timeout=120,
        )
        response.raise_for_status()
        return response.text
    except (httpx.HTTPError, httpx.RequestError):
        raise ValueError(f"Unsupported or unreadable document format: {filename}")


def chunk_text(text: str, max_chars: int = 2048) -> list[str]:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= max_chars:
            current = f"{current}\n\n{paragraph}".strip()
            continue
        if current:
            chunks.append(current)
        if len(paragraph) <= max_chars:
            current = paragraph
            continue
        for start in range(0, len(paragraph), max_chars):
            segment = paragraph[start:start + max_chars].strip()
            if segment:
                chunks.append(segment)
        current = ""

    if current:
        chunks.append(current)
    return chunks
