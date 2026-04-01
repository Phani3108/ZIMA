"""
Text chunker — splits documents into token-bounded chunks.
Pattern adapted from RDT 6/ingest/md_chunker.py.

Each chunk gets metadata for filtering/attribution in Qdrant.
"""

import uuid
from dataclasses import dataclass, field
from typing import List

try:
    import tiktoken
    _enc = tiktoken.get_encoding("cl100k_base")
    def _count_tokens(text: str) -> int:
        return len(_enc.encode(text))
except ImportError:
    def _count_tokens(text: str) -> int:
        return len(text.split())  # fallback: word count

MAX_TOKENS = 300
OVERLAP_SENTENCES = 1


@dataclass
class Chunk:
    text: str
    chunk_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_type: str = ""    # "file", "url", "confluence", "teams_chat"
    source_name: str = ""    # filename, url, page title, etc.
    source_url: str = ""
    page_num: int = 0
    ingested_at: str = ""


def chunk_text(
    text: str,
    source_type: str = "",
    source_name: str = "",
    source_url: str = "",
) -> List[Chunk]:
    """
    Split text into token-bounded chunks with metadata.
    Splits on double newlines (paragraphs), then falls back to sentence splitting.
    """
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks: List[Chunk] = []
    current_parts: List[str] = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = _count_tokens(para)

        # Paragraph itself is too long — split by sentence
        if para_tokens > MAX_TOKENS:
            sentences = _split_sentences(para)
            for sent in sentences:
                st = _count_tokens(sent)
                if current_tokens + st > MAX_TOKENS and current_parts:
                    chunks.append(_make_chunk(current_parts, source_type, source_name, source_url, now))
                    # Overlap: keep last sentence
                    current_parts = current_parts[-OVERLAP_SENTENCES:]
                    current_tokens = sum(_count_tokens(p) for p in current_parts)
                current_parts.append(sent)
                current_tokens += st
        else:
            if current_tokens + para_tokens > MAX_TOKENS and current_parts:
                chunks.append(_make_chunk(current_parts, source_type, source_name, source_url, now))
                current_parts = current_parts[-OVERLAP_SENTENCES:]
                current_tokens = sum(_count_tokens(p) for p in current_parts)
            current_parts.append(para)
            current_tokens += para_tokens

    if current_parts:
        chunks.append(_make_chunk(current_parts, source_type, source_name, source_url, now))

    return chunks


def _make_chunk(parts, source_type, source_name, source_url, ingested_at) -> Chunk:
    return Chunk(
        text="\n\n".join(parts),
        source_type=source_type,
        source_name=source_name,
        source_url=source_url,
        ingested_at=ingested_at,
    )


def _split_sentences(text: str) -> List[str]:
    """Simple sentence splitter on '. ', '! ', '? '."""
    import re
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]
