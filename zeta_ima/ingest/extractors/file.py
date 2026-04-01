"""
File extractor — PDF, Word (.docx), and plain text.
Returns plain text string from file bytes.
"""

import io


def extract_text(file_bytes: bytes, filename: str) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        return _from_pdf(file_bytes)
    elif name.endswith(".docx"):
        return _from_docx(file_bytes)
    else:
        return file_bytes.decode("utf-8", errors="replace")


def _from_pdf(data: bytes) -> str:
    import fitz  # pymupdf
    doc = fitz.open(stream=data, filetype="pdf")
    pages = []
    for page in doc:
        pages.append(page.get_text())
    return "\n\n".join(pages)


def _from_docx(data: bytes) -> str:
    from docx import Document
    doc = Document(io.BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
