# PaperMind

**NLP & LLM-Powered Research Paper Intelligence Engine**

Upload research papers (PDF) and get structured summaries, semantic search,
grounded Q&A (RAG), and side-by-side paper comparison — all with citations
back to the source text.

> **Status: Phase 4 — Chunking + Embeddings.** Every processed paper is now
> automatically split into sentence-aware chunks (tagged with page number
> and detected section), embedded with Sentence-Transformers, and indexed
> in a persistent FAISS vector store. Semantic search is not yet exposed via
> the API/UI — that's Phase 5. Verify indexing works using the CLI script
> described below. RAG and LLM features are added in later phases.

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
| `LLM_PROVIDER` | `ollama` \| `openai` \| `gemini` | `ollama` |
| `LLM_MODEL` | Model name for the chosen provider | `llama3.1` |
| `OLLAMA_BASE_URL` | Local Ollama server URL | `http://localhost:11434` |
| `OPENAI_API_KEY` / `GEMINI_API_KEY` | Only needed if switching provider | *(empty)* |

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
- [ ] Phase 3 — NLP processing (section detection, NER, entity extraction)
- [ ] Phase 4 — Chunking + embeddings + FAISS index
- [ ] Phase 5 — Semantic search
- [ ] Phase 6 — RAG + question answering
- [ ] Phase 7 — Automatic structured summary
- [ ] Phase 8 — Paper comparison
- [ ] Phase 9 — Dashboard
- [ ] Phase 10 — Final polish, tests, docs
