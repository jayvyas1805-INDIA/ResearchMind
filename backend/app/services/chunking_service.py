"""
Chunking service.

Splits each page's text into sentence-aware chunks of roughly
CHUNK_TARGET_WORDS words, without splitting sentences mid-way. Each chunk
is tagged with:
  - chunk_index (order within the paper)
  - page_number (which page it came from)
  - section (best-effort match against the sections detected in Phase 3)

Kept independent of FastAPI/DB — returns plain dataclasses.
"""

from dataclasses import dataclass
import re
from typing import Dict, List

from app.core.config import get_settings
from app.services.nlp_service import get_nlp

settings = get_settings()


@dataclass
class PageInput:
    page_number: int
    text: str


@dataclass
class ChunkData:
    chunk_index: int
    page_number: int
    section: str
    text: str


def _split_page_into_sentences(text: str) -> List[str]:
    nlp = get_nlp()
    doc = nlp(text)
    return [s.text.strip() for s in doc.sents if s.text.strip()]


def _group_sentences_into_chunks(
    sentences: List[str],
    target_words: int,
    min_words: int,
) -> List[str]:
    """Group consecutive sentences into chunks near `target_words` long."""
    chunks: List[str] = []
    current: List[str] = []
    current_words = 0

    for sentence in sentences:
        sentence_words = len(sentence.split())
        if current and current_words + sentence_words > target_words:
            chunks.append(" ".join(current))
            current = [sentence]
            current_words = sentence_words
        else:
            current.append(sentence)
            current_words += sentence_words

    if current:
        chunk_text = " ".join(current)
        # Merge a too-small trailing chunk into the previous one rather than
        # storing a near-empty fragment.
        if chunks and current_words < min_words:
            chunks[-1] = chunks[-1] + " " + chunk_text
        else:
            chunks.append(chunk_text)

    return chunks


def _best_matching_section(chunk_text: str, sections: Dict[str, str]) -> str:
    """
    Best-effort: find the most specific (shortest) detected section whose
    content contains this chunk's text. Falls back to "unclassified".

    We prefer the shortest containing section so a catch-all like
    "full_text" or "preamble" doesn't win over a more specific section.
    """
    probe = re.sub(r"\s+", " ", chunk_text[:120]).strip().casefold()
    if not probe:
        return "unclassified"

    best_name = None
    best_len = None
    for name, content in sections.items():
        if name in ("preamble",):
            continue
        normalized_content = re.sub(r"\s+", " ", content).casefold()
        if probe in normalized_content:
            if best_len is None or len(normalized_content) < best_len:
                best_name = name
                best_len = len(normalized_content)

    return best_name or "unclassified"


def chunk_paper(
    pages: List[PageInput],
    sections: Dict[str, str],
    target_words: int = None,
    min_words: int = None,
) -> List[ChunkData]:
    """
    Full chunking pipeline for one paper.

    Args:
        pages: page-level text, in page order.
        sections: canonical_section_name -> section content, from Phase 3.
        target_words / min_words: override settings.CHUNK_TARGET_WORDS /
            settings.CHUNK_MIN_WORDS for this call (used by the ablation
            study to compare chunk sizes without touching global config).

    Returns:
        Ordered list of ChunkData, chunk_index assigned sequentially across
        the whole paper (not reset per page).
    """
    target_words = target_words if target_words is not None else settings.CHUNK_TARGET_WORDS
    min_words = min_words if min_words is not None else settings.CHUNK_MIN_WORDS

    all_chunks: List[ChunkData] = []
    chunk_index = 0

    for page in pages:
        if not page.text or not page.text.strip():
            continue

        sentences = _split_page_into_sentences(page.text)
        if not sentences:
            continue

        page_chunks = _group_sentences_into_chunks(
            sentences,
            target_words=target_words,
            min_words=min_words,
        )

        for chunk_text in page_chunks:
            section = _best_matching_section(chunk_text, sections)
            all_chunks.append(
                ChunkData(
                    chunk_index=chunk_index,
                    page_number=page.page_number,
                    section=section,
                    text=chunk_text,
                )
            )
            chunk_index += 1

    return all_chunks
