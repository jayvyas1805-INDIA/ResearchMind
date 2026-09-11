"""
Tests for chunking_service's grouping/section-matching logic. Sentence
splitting itself needs spaCy loaded, so these tests are skipped gracefully
if the model isn't installed (e.g. CI without `spacy download` run yet).
"""
import pytest

from app.services import chunking_service


def _spacy_model_available() -> bool:
    try:
        from app.services.nlp_service import get_nlp
        get_nlp()
        return True
    except Exception:
        return False


requires_spacy = pytest.mark.skipif(
    not _spacy_model_available(), reason="spaCy model 'en_core_web_sm' not installed"
)


def test_group_sentences_into_chunks_respects_target_size():
    sentences = ["This is sentence number " + str(i) + " with several words in it." for i in range(20)]
    chunks = chunking_service._group_sentences_into_chunks(sentences, target_words=50, min_words=10)
    assert len(chunks) > 1
    for chunk in chunks:
        assert isinstance(chunk, str) and chunk.strip()


def test_best_matching_section_picks_most_specific():
    sections = {
        "full_text": "intro text. Method: we used BERT. results here.",
        "methodology": "Method: we used BERT.",
    }
    result = chunking_service._best_matching_section("Method: we used BERT.", sections)
    assert result == "methodology"


def test_best_matching_section_falls_back_to_unclassified():
    sections = {"abstract": "This paper is about cats."}
    result = chunking_service._best_matching_section("Completely unrelated text here.", sections)
    assert result == "unclassified"


@requires_spacy
def test_chunk_paper_preserves_page_numbers():
    pages = [
        chunking_service.PageInput(page_number=1, text="This is page one. It has two sentences."),
        chunking_service.PageInput(page_number=2, text="This is page two. It also has content."),
    ]
    chunks = chunking_service.chunk_paper(pages, sections={})
    assert all(c.page_number in (1, 2) for c in chunks)
    assert any(c.page_number == 1 for c in chunks)
    assert any(c.page_number == 2 for c in chunks)
