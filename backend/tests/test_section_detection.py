"""
Tests for section detection and text cleaning — pure regex/string logic in
nlp_service, no spaCy model load required.
"""
from app.services import nlp_service


def test_clean_text_collapses_whitespace_and_formfeeds():
    raw = "Line one\x0c\n\n\n\nLine two   with   spaces  "
    cleaned = nlp_service.clean_text(raw)
    assert "\x0c" not in cleaned
    assert "\n\n\n" not in cleaned
    assert "   " not in cleaned


def test_detect_sections_finds_known_headers():
    text = (
        "Some Paper Title\nJane Doe, John Smith\n\n"
        "Abstract\nThis paper studies X.\n\n"
        "1. Introduction\nX is important because Y.\n\n"
        "Methodology\nWe use model Z.\n\n"
        "Results\nWe achieved 90% accuracy.\n\n"
        "Conclusion\nWe conclude that X works.\n"
    )
    sections = nlp_service.detect_sections(text)
    assert "abstract" in sections
    assert "This paper studies X." in sections["abstract"]
    assert "methodology" in sections
    assert "We use model Z." in sections["methodology"]
    assert "results" in sections
    assert "conclusion" in sections
    assert "preamble" in sections  # title/authors before first header


def test_detect_sections_falls_back_to_full_text_when_no_headers_found():
    text = "Just some plain paragraph text with no recognizable section headers at all."
    sections = nlp_service.detect_sections(text)
    assert sections == {"full_text": text.strip()}


def test_extract_title_authors_uses_first_two_lines():
    preamble = "A Great Paper Title\nAlice, Bob\nUniversity of Somewhere"
    title, authors = nlp_service.extract_title_authors(preamble)
    assert title == "A Great Paper Title"
    assert authors == "Alice, Bob"


def test_extract_title_authors_handles_empty_preamble():
    title, authors = nlp_service.extract_title_authors("")
    assert title is None
    assert authors is None
