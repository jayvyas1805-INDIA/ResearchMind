# Retrieval Evaluation Harness

Answers the question an interviewer will actually ask: **"how do you know
your retrieval works?"**

## Quick start (synthetic fixture paper)

```bash
cd backend
source .venv/bin/activate
python eval/seed_fixture_paper.py
python eval/run_eval.py eval/qa_sets/fixture_paper.json --k 1,3,5,10
```

This seeds a small 4-page synthetic paper with known facts on known pages,
then measures whether retrieval actually surfaces the right page for each
question — no LLM calls, no manual PDF needed, runs in seconds.

## Metrics

- **Recall@k** — for what fraction of questions did the correct page appear
  somewhere in the top k results? This is the metric that matters most for
  RAG: if the right chunk isn't retrieved, the LLM can't answer correctly
  no matter how good the prompt is.
- **MRR (Mean Reciprocal Rank)** — averages `1/rank` of the first correct
  hit across questions. Rewards ranking the right answer *higher*, not just
  including it somewhere in top-k.

## Building a QA set for one of your real papers

1. Upload and process a real paper through PaperMind as usual, note its `paper_id` (from `GET /api/papers`).
2. Read through the paper and write 15-30 questions you could reasonably ask about it.
3. For each question, note which page(s) actually contain the answer.
4. Save as `eval/qa_sets/<your_paper_name>.json`, following the same shape as `fixture_paper.json`:

```json
{
  "paper_id": "<the real paper_id>",
  "description": "optional note to yourself",
  "questions": [
    {"question": "What dataset was used?", "relevant_pages": [3]},
    {"question": "What was the reported F1 score?", "relevant_pages": [7, 8]}
  ]
}
```

5. Run: `python eval/run_eval.py eval/qa_sets/<your_paper_name>.json --save`

`--save` writes a timestamped JSON report to `eval/results/` so you can
compare runs later — this is what the upcoming ablation study (Phase 12)
will diff against when you change chunk size, embedding model, or add
reranking.

## What "good" looks like

There's no universal threshold, but as a rough sanity check for a small
demo paper: Recall@5 below ~0.6 usually means something is off (chunking
too coarse/fine, wrong embedding model, or genuinely ambiguous questions)
worth investigating before blaming the LLM for a bad answer.
