"""
NLP processing service.

Takes the raw text extracted from a PDF (Phase 2) and produces structured
information:
  - cleaned text
  - detected sections (Abstract, Introduction, Methodology, Results, ...)
  - title / authors (best-effort heuristics)
  - sentences
  - named entities: PERSON / ORGANIZATION (generic spaCy NER)
  - research entities: MODEL / DATASET / METRIC / METHOD / TECHNOLOGY
    (custom rule-based layer — generic NER does not have these categories
    and would mislabel them, so we do not rely on it for these)

Kept independent of FastAPI so it can be reused/tested without the API layer.
"""

import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, List, Optional

import spacy
from spacy.matcher import PhraseMatcher

from app.utils.research_terms import ALL_CATEGORIES

# ---------------------------------------------------------------------------
# spaCy model loading (singleton — loading is expensive, do it once)
# ---------------------------------------------------------------------------

_SPACY_MODEL_NAME = "en_core_web_sm"


@lru_cache
def get_nlp():
    """
    Load the spaCy pipeline once and cache it.

    Requires the model to be downloaded first:
        python -m spacy download en_core_web_sm
    """
    try:
        return spacy.load(_SPACY_MODEL_NAME)
    except OSError as exc:
        raise RuntimeError(
            f"spaCy model '{_SPACY_MODEL_NAME}' is not installed. "
            f"Run: python -m spacy download {_SPACY_MODEL_NAME}"
        ) from exc


@lru_cache
def get_phrase_matcher() -> PhraseMatcher:
    """Build a PhraseMatcher over all curated research-term categories."""
    nlp = get_nlp()
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    for category, terms in ALL_CATEGORIES.items():
        patterns = [nlp.make_doc(term) for term in terms]
        matcher.add(category, patterns)
    return matcher


# ---------------------------------------------------------------------------
# Section detection
# ---------------------------------------------------------------------------

# Canonical section name -> regex alternatives that appear as headers in papers.
SECTION_PATTERNS: Dict[str, str] = {
    "abstract": r"abstract",
    "introduction": r"introduction",
    "related_work": r"related work|background|literature review",
    "methodology": r"methodology|methods|method|approach|proposed method|proposed approach",
    "experiments": r"experiments?|experimental setup|experimental results",
    "results": r"results|evaluation",
    "discussion": r"discussion",
    "limitations": r"limitations?",
    "conclusion": r"conclusions?|concluding remarks|future work",
    "acknowledgments": r"acknowledg(e)?ments?",
    "references": r"references|bibliography",
}

# A line is considered a "header" if it's short, and matches a known section
# name (optionally preceded by numbering like "1.", "II.", "3)").
_HEADER_LINE_RE = re.compile(
    r"^\s*(?:[0-9]+\.?|[IVXLC]+\.?)?\s*(" + "|".join(SECTION_PATTERNS.values()) + r")\s*[:.]?\s*$",
    re.IGNORECASE,
)


def _canonical_section_name(matched_text: str) -> str:
    matched_lower = matched_text.strip().lower()
    for canonical, pattern in SECTION_PATTERNS.items():
        if re.fullmatch(pattern, matched_lower, re.IGNORECASE):
            return canonical
    return matched_lower


def detect_sections(text: str) -> Dict[str, str]:
    """
    Heuristically split the paper's text into named sections based on
    header-like lines. Returns a dict of canonical_section_name -> content.

    Uncertain/ambiguous cases fall back gracefully: if no headers are found
    at all, the entire text is returned under "full_text".
    """
    lines = text.split("\n")
    header_positions: List[tuple] = []  # (line_index, canonical_name)

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or len(stripped) > 60:
            continue
        match = _HEADER_LINE_RE.match(stripped)
        if match:
            canonical = _canonical_section_name(match.group(1))
            header_positions.append((i, canonical))

    if not header_positions:
        return {"full_text": text.strip()}

    sections: Dict[str, str] = {}

    # Content before the first header — usually title/authors/affiliations.
    pre_header_text = "\n".join(lines[: header_positions[0][0]]).strip()
    if pre_header_text:
        sections["preamble"] = pre_header_text

    for idx, (line_idx, name) in enumerate(header_positions):
        start = line_idx + 1
        end = header_positions[idx + 1][0] if idx + 1 < len(header_positions) else len(lines)
        content = "\n".join(lines[start:end]).strip()
        # If the same section name appears twice (rare), keep the longer content.
        if name in sections and len(sections[name]) >= len(content):
            continue
        sections[name] = content

    return sections


# ---------------------------------------------------------------------------
# Text cleaning
# ---------------------------------------------------------------------------

def clean_text(raw_text: str) -> str:
    """Normalize whitespace and strip common PDF extraction noise."""
    text = raw_text.replace("\x0c", "\n")  # form-feed -> newline
    # Collapse 3+ blank lines into a single blank line.
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Collapse runs of spaces/tabs.
    text = re.sub(r"[ \t]{2,}", " ", text)
    # Trim trailing whitespace on each line.
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return text.strip()


# ---------------------------------------------------------------------------
# Title / authors heuristic extraction
# ---------------------------------------------------------------------------

def extract_title_authors(preamble: str) -> tuple:
    """
    Best-effort heuristic: in most papers, the title is the first substantial
    line before the abstract/authors block, and authors follow on the next
    non-empty line(s) before affiliations/emails.

    This is inherently uncertain across paper formats — kept intentionally
    simple and documented as a heuristic, not a guarantee.
    """
    if not preamble:
        return None, None

    lines = [ln.strip() for ln in preamble.split("\n") if ln.strip()]
    if not lines:
        return None, None

    title = lines[0]

    authors = None
    if len(lines) > 1:
        # Author lines often contain commas, "and", or superscript-like digits;
        # avoid grabbing a second title-like line by capping length.
        candidate = lines[1]
        if len(candidate) < 200:
            authors = candidate

    return title, authors


# ---------------------------------------------------------------------------
# Entity extraction
# ---------------------------------------------------------------------------

@dataclass
class ExtractedEntities:
    persons: List[str] = field(default_factory=list)
    organizations: List[str] = field(default_factory=list)
    models: List[str] = field(default_factory=list)
    datasets: List[str] = field(default_factory=list)
    metrics: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)
    technologies: List[str] = field(default_factory=list)


def extract_entities(text: str, max_chars: int = 100_000) -> ExtractedEntities:
    """
    Run generic NER (PERSON/ORG via spaCy) and custom rule-based matching
    (MODEL/DATASET/METRIC/METHOD/TECHNOLOGY via curated phrase lists) over
    the text.

    We deliberately do NOT ask spaCy's generic NER for MODEL/DATASET/etc. —
    those aren't categories it knows, and mapping something like "ORG" onto
    "MODEL" would be unreliable. The curated PhraseMatcher lists are the
    source of truth for those categories.
    """
    nlp = get_nlp()
    matcher = get_phrase_matcher()

    # Guard against extremely long papers slowing down processing.
    truncated = text[:max_chars]
    doc = nlp(truncated)

    persons = set()
    organizations = set()
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            persons.add(ent.text.strip())
        elif ent.label_ == "ORG":
            organizations.add(ent.text.strip())

    category_hits: Dict[str, set] = {cat: set() for cat in ALL_CATEGORIES}
    for match_id, start, end in matcher(doc):
        category = nlp.vocab.strings[match_id]
        span_text = doc[start:end].text
        category_hits[category].add(span_text)

    return ExtractedEntities(
        persons=sorted(persons)[:50],
        organizations=sorted(organizations)[:50],
        models=sorted(category_hits["models"]),
        datasets=sorted(category_hits["datasets"]),
        metrics=sorted(category_hits["metrics"]),
        methods=sorted(category_hits["methods"]),
        technologies=sorted(category_hits["technologies"]),
    )


# ---------------------------------------------------------------------------
# Sentence segmentation
# ---------------------------------------------------------------------------

def split_sentences(text: str, max_chars: int = 100_000) -> List[str]:
    nlp = get_nlp()
    doc = nlp(text[:max_chars])
    return [sent.text.strip() for sent in doc.sents if sent.text.strip()]


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

@dataclass
class NLPResult:
    cleaned_text: str
    sections: Dict[str, str]
    title: Optional[str]
    authors: Optional[str]
    entities: ExtractedEntities
    sentence_count: int


def run_nlp_pipeline(raw_text: str) -> NLPResult:
    """
    Full Phase 3 pipeline:
      clean -> detect sections -> extract title/authors -> NER + custom
      entity extraction -> sentence segmentation.
    """
    cleaned = clean_text(raw_text)
    sections = detect_sections(cleaned)

    title, authors = extract_title_authors(sections.get("preamble", ""))
    entities = extract_entities(cleaned)
    sentences = split_sentences(cleaned)

    return NLPResult(
        cleaned_text=cleaned,
        sections=sections,
        title=title,
        authors=authors,
        entities=entities,
        sentence_count=len(sentences),
    )
