# PaperMind

**NLP & LLM-Powered Research Paper Intelligence Engine**

Upload research papers (PDF) and get structured summaries, semantic search,
grounded Q&A (RAG), and side-by-side paper comparison — all with citations
back to the source text.

> **Status: Complete (Phases 1-10).** Full pipeline: upload → extract →
> NLP (sections, entities) → chunk → embed → FAISS index → semantic search →
> RAG Q&A → structured summary → paper comparison, with a Dashboard/Papers/
> Search/Ask/Compare/Settings UI, basic tests, logging, and error handling
> throughout.

---

## Architecture

```
PDF Upload → Text Extraction → Cleaning & Section Detection → NLP Extraction
→ Chunking → Embeddings → Vector DB → Semantic Search → RAG → LLM
→ Summary / Q&A / Comparison
```

```
PaperMind/
├── backend/           FastAPI app
│   └── app/
│       ├── main.py    entrypoint
│       ├── core/      config
│       ├── api/       routes
│       ├── models/    DB models      (Phase 2+)
│       ├── schemas/   pydantic schemas (Phase 2+)
│       ├── services/  business logic (Phase 2+)
│       └── utils/
└── frontend/          React + Vite + Tailwind app
    └── src/
        ├── components/
        ├── pages/
        ├── services/
        ├── hooks/      (Phase 2+)
        └── types/      (Phase 2+)
```

---

## Prerequisites

- **Python 3.12** (recommended). If you have multiple Python versions
  installed (e.g. 3.12 and 3.13), use 3.12 explicitly — libraries needed in
  later phases (spaCy, faiss-cpu, sentence-transformers) can lag behind the
  newest Python release and may not yet have compatible wheels for 3.13.
- Node.js 18+
- (Later phases) [Ollama](https://ollama.com) installed locally, since the
  default LLM provider is a local open-source model.

---

## Backend — Setup & Run

```bash
cd backend

# Use Python 3.12 explicitly if your system default is a newer version
python3.12 -m venv .venv          # Windows: py -3.12 -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate

# Confirm the venv is actually on 3.12 before installing anything
python --version                  # should print Python 3.12.x

pip install --upgrade pip
pip install -r requirements.txt

cp .env.example .env              # edit values if needed
python -m uvicorn app.main:app --reload --port 8010
```

Backend will be running at: **http://localhost:8010**
Interactive API docs: **http://localhost:8010/docs**

> Using port 8010 (instead of the common 8000) to avoid clashing with other
> local projects that often default to 8000.

> **Phase 3 requirement:** after `pip install -r requirements.txt`, also run:
> ```bash
> python -m spacy download en_core_web_sm
> ```
> The NLP pipeline needs this model for sentence segmentation and named
> entity recognition — the server will raise a clear error on first use if
> it's missing.

### Endpoints to test

**Phase 1 — health check**
```
GET http://localhost:8010/api/health
```
Expected response:
```json
{ "status": "ok", "app": "PaperMind", "environment": "development" }
```

**Phase 2 — upload a paper**
```
POST http://localhost:8010/api/papers/upload
Content-Type: multipart/form-data
Body: file=<your PDF>
```
Try it from the interactive docs at `http://localhost:8010/docs`, or via curl:
```bash
curl -X POST http://localhost:8010/api/papers/upload \
  -F "file=@/path/to/some_paper.pdf"
```
Expected response:
```json
{
  "paper_id": "b6e2b6b0-...",
  "filename": "some_paper.pdf",
  "page_count": 12,
  "status": "processed"
}
```

**Phase 2 — list uploaded papers**
```
GET http://localhost:8010/api/papers
```

**Phase 2 — get one paper's detail**
```
GET http://localhost:8010/api/papers/{paper_id}
```

**Error handling to verify:**
- Upload a non-PDF file → `400 Bad Request`
- Upload a PDF with no extractable text (e.g. a blank/scanned page) → `422 Unprocessable Entity`
- Upload a file larger than `MAX_UPLOAD_SIZE_MB` → `400 Bad Request`

**Phase 3 — NLP processing (runs automatically as part of upload)**

After upload, the response's `status` will be `processed` if NLP succeeded,
or `failed` if extraction worked but NLP processing hit an error (check
`error_message` on the paper detail endpoint in that case — the extracted
text is still preserved either way).

```
GET http://localhost:8010/api/papers/{paper_id}
```
Now also returns: `abstract`, `methodology`, `results_section`,
`limitations`, `conclusion`, and `entities` (models, datasets, metrics,
methods, technologies, organizations, persons).

```
POST http://localhost:8010/api/papers/{paper_id}/analyze
```
Re-runs the NLP pipeline on a paper's already-extracted text (no re-upload
needed) — useful after tweaking the entity keyword lists in
`app/utils/research_terms.py`.

On the frontend: click a paper's title on the Dashboard to open its detail
page, showing detected sections and extracted entities as chips, with a
"Re-run NLP analysis" button.

**Phase 4 — chunking + embeddings + FAISS (runs automatically after NLP)**

Every successfully-processed paper is automatically chunked and indexed —
no separate step needed. There's no public search API yet (that's Phase 5),
so verify indexing worked using the included CLI script:

```bash
cd backend
source .venv/bin/activate
python scripts/test_retrieval.py <paper_id> "what dataset was used"
```

Get a `paper_id` from `GET /api/papers`. Expected output: the top 5 matching
chunks with similarity scores, page numbers, and detected sections.

> First run downloads the `all-MiniLM-L6-v2` model (~90MB) from Hugging
> Face automatically — needs internet once, then it's cached locally.

The FAISS index is persisted at `backend/indexes/papermind.faiss` and
reloaded on server restart (no rebuild needed). Re-uploading or re-analyzing
a paper safely re-indexes it (old vectors are removed first).

---

## Frontend — Setup & Run

```bash
cd frontend
npm install

cp .env.example .env             # edit values if needed
npm run dev
```

Frontend will be running at: **http://localhost:5173**

You should see the PaperMind navbar with **Dashboard** and **Upload**
placeholder pages.

---

## Environment Variables

### `backend/.env`

| Variable | Purpose | Default |
|---|---|---|
| `DATABASE_URL` | SQLite connection string | `sqlite:///./data/papermind.db` |
| `UPLOAD_DIR` | Where uploaded PDFs are stored | `./data/uploads` |
| `INDEX_DIR` | Where the FAISS index is persisted | `./indexes` |
| `EMBEDDING_MODEL` | Sentence-Transformers model name | `all-MiniLM-L6-v2` |
| `EMBEDDING_DIM` | Must match the model's output dimension | `384` |
| `CHUNK_TARGET_WORDS` | Target words per chunk | `180` |
| `CHUNK_MIN_WORDS` | Trailing chunks smaller than this get merged | `40` |
| `DEFAULT_TOP_K` | Default number of search results | `5` |
| `LLM_PROVIDER` | `ollama` \| `openai` \| `gemini` \| `mistral` | `ollama` |
| `LLM_MODEL` | Model name for the chosen provider | `llama3.1` |
| `OLLAMA_BASE_URL` | Local Ollama server URL | `http://localhost:11434` |
| `OPENAI_API_KEY` / `GEMINI_API_KEY` / `MISTRAL_API_KEY` | Only needed for the matching cloud provider | *(empty)* |

For Mistral, set `LLM_PROVIDER=mistral`, `LLM_MODEL=mistral-small-latest`,
and `MISTRAL_API_KEY` in `backend/.env`. Keep API keys out of source control.

### `frontend/.env`

| Variable | Purpose | Default |
|---|---|---|
| `VITE_API_BASE_URL` | Backend API base URL | `http://localhost:8010/api` |

**No secrets are hardcoded anywhere in the codebase** — everything sensitive
is read from environment variables.

---

## Roadmap (implemented phase by phase)

- [x] Phase 1 — Project setup
- [x] Phase 2 — PDF upload & extraction
- [x] Phase 3 — NLP processing
- [x] Phase 4 — Chunking + embeddings + FAISS index
- [x] Phase 5 — Semantic search
- [x] Phase 6 — RAG + question answering
- [x] Phase 7 — Automatic structured summary
- [x] Phase 8 — Paper comparison
- [x] Phase 9 — Dashboard
- [x] Phase 10 — Final polish, tests, docs

---

## API Endpoints (complete list)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Health check |
| POST | `/api/papers/upload` | Upload a PDF → extract, NLP-process, chunk, embed, index |
| GET | `/api/papers` | List all papers |
| GET | `/api/papers/{id}` | Paper detail (sections + entities) |
| POST | `/api/papers/{id}/analyze` | Re-run NLP + re-index without re-uploading |
| GET/POST | `/api/papers/{id}/search` | Retrieve relevant source passages (hybrid BM25+vector ranking is enabled by default in the portal) |
| POST | `/api/papers/{id}/chat` | Ask a grounded question (RAG) |
| GET/POST | `/api/papers/{id}/summary` | Structured 9-field summary (cached) |
| POST | `/api/papers/compare` | Compare two papers |
| GET | `/api/settings` | Read-only backend config (for the Settings page) |
| GET | `/api/leaderboard` | Cross-paper structured results (filter by `dataset`, `metric`, `model`, `min_value`) |
| GET | `/api/leaderboard/facets` | Distinct dataset/metric/model values, for filter dropdowns |

## How RAG works here

1. Your question is embedded with the same Sentence-Transformers model used for indexing.
2. FAISS returns the most similar chunks (with page/section metadata) for that paper.
3. Those chunks — not the full PDF — are assembled into a context block.
4. The LLM is instructed to answer **only** from that context and say so explicitly if the answer isn't present, rather than guessing.
5. The API returns the answer alongside the exact source chunks used, so you can verify it.

Search returns ranked passages rather than composing an answer; use **Ask a
Paper** when you want a direct response. If the configured LLM provider is
unavailable, Ask returns relevant source sentences, and summary/comparison
use clearly labeled extractive results instead. These fallbacks quote or
compare extracted paper content; they do not replace a working LLM. A
provider quota or account error (for example Mistral HTTP 429) still needs to
be resolved with that provider.

## Running the tests

```bash
cd backend
source .venv/bin/activate
pytest
```

Most tests mock FAISS/the embedding model/the LLM so they run fast without
extra setup. A few chunking tests need `en_core_web_sm` installed and are
skipped automatically if it isn't.

## Retrieval evaluation harness

Answers "how do you know retrieval actually works?" with real numbers
(Recall@k, MRR) instead of a vibe check:

```bash
python eval/seed_fixture_paper.py
python eval/run_eval.py eval/qa_sets/fixture_paper.json --k 1,3,5,10
```

See `eval/README.md` for metric definitions and how to build a QA set
against one of your own uploaded papers.

## Beyond ChatGPT-style summarization: cross-paper leaderboard

The features above (search, RAG Q&A, summary) are useful, but someone
could reasonably ask "couldn't I just paste this PDF into ChatGPT?" This
feature is the answer to that: a **persistent, structured, filterable
table of numeric results extracted across your entire paper library** —
not a one-off generated answer, a database that grows and stays queryable
as you upload more papers. ChatGPT starts from zero every conversation;
this doesn't.

**How extraction works** (`app/services/results_extraction_service.py`):
pattern-based, not another LLM call. For each sentence, find a metric term
(Accuracy, F1, BLEU, ...) near a number (percentage or decimal), then
attach any model/dataset names that co-occur in that same sentence. Every
claim keeps its exact source sentence and page number for verification —
click a row on the Leaderboard page to see it.

Runs automatically as part of upload/analyze. Browse and filter at
`GET /api/leaderboard?dataset=...&metric=...&model=...`, or the
Leaderboard page in the UI.

**Known limitation, stated plainly**: this only catches results phrased
with a metric name near a number in the same sentence — it will miss
results reported in tables (PDF table extraction isn't implemented) or
phrased unusually. It's a precision-over-recall design: better to show
fewer, verifiable claims with their exact source sentence than to guess.

## Ablation study

Rather than assuming chunk size / embedding model choices are good, this
script measures them, varying one knob at a time against the fixture QA
set — entirely in an isolated in-memory index, so it never touches the
live app's data:

```bash
python eval/ablation.py
python eval/ablation.py --save   # also writes a markdown write-up template
```

Default experiments: chunk size 100 vs 180 (current default) vs 300 words,
and `all-MiniLM-L6-v2` vs `all-mpnet-base-v2` embeddings. Edit
`DEFAULT_EXPERIMENTS` in `eval/ablation.py` to add your own — e.g. different
`top_k`, a different NLI groundedness threshold, or hybrid vs vector-only
(already covered by `run_eval.py --hybrid`, see above).

This — a table of "I tried X, here's what changed, here's why" — is the
actual artifact worth bringing to an interview, more than any single
feature in the app.

## Stretch: fine-tuned NER

`backend/training/` contains a full weak-supervision fine-tuning pipeline
that upgrades entity extraction beyond the rule-based PhraseMatcher —
including an honest evaluation design (never test the trained model
against the same rule-based labels it was trained to imitate). See
`training/README.md` for the full workflow and why the evaluation is
built the way it is. This is a standalone research artifact; the live app
still uses the rule-based extractor by default.

## Hybrid retrieval (BM25 + vector fusion)

Pure vector similarity can miss exact-term matches — model names, dataset
names, specific numbers — that a keyword search catches trivially. Hybrid
retrieval fuses a BM25 lexical ranking with the vector ranking via
Reciprocal Rank Fusion (RRF), which is standard practice in production RAG.

Enable it per-request: `use_hybrid: true` in the POST body, `?hybrid=true`
on the GET route, or the checkbox on the Search page. To prove it actually
helps rather than just assuming it does, compare it against vector-only on
the same QA set:

```bash
python eval/run_eval.py eval/qa_sets/fixture_paper.json --save
python eval/run_eval.py eval/qa_sets/fixture_paper.json --hybrid --save
```

Both reports land in `eval/results/` with `_vector`/`_hybrid` suffixes so
you can diff Recall@k and MRR directly — this before/after comparison is
the artifact worth bringing to an interview, not the feature itself.

## Groundedness / hallucination checking

Telling the LLM "only answer from context" is a prompt, not a guarantee.
After generating an answer, PaperMind independently checks it using an
NLI (Natural Language Inference) cross-encoder: each sentence in the
answer is tested against every retrieved chunk to see if any chunk actually
*entails* it. Sentences with no supporting chunk are flagged.

The chat API returns `is_grounded`, `supported_ratio`, and per-sentence
`sentence_grounding` (each with its support score and which source chunk
backs it). The Ask Paper UI shows this as an expandable badge under each
answer.

This is a genuinely independent check, not just the LLM's own self-report —
it catches the case where an LLM ignores its instructions and adds a
plausible but unsupported detail. Configure via `.env`:
`GROUNDEDNESS_CHECK_ENABLED`, `NLI_MODEL`, `GROUNDEDNESS_SUPPORT_THRESHOLD`,
`GROUNDEDNESS_SENTENCE_RATIO_THRESHOLD`. First use downloads
`cross-encoder/nli-deberta-v3-small` (~140MB) automatically.

## Known limitations / possible future work

- Single-user, local-first design — no auth/multi-tenancy (out of scope for a student project, but the FastAPI/SQLAlchemy structure supports adding it).
- FAISS `IndexFlatIP` is exact but not sharded — fine at student-project scale; ChromaDB/Qdrant would be the next step at larger scale (the codebase already isolates this behind `vector_service.py`).
- Section detection and title/author extraction are heuristic (regex-based) and can miss on unusually formatted papers — the raw extracted text is always preserved as a fallback.
- No OCR — scanned/image-only PDFs are rejected with a clear error rather than silently producing empty results.
- Duplicate-upload detection is by exact file content hash — near-duplicate PDFs (different formatting, exports) aren't caught.
