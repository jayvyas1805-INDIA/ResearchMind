# PaperMind

**NLP & LLM-Powered Research Paper Intelligence Engine**

Upload research papers (PDF) and get structured summaries, semantic search,
grounded Q&A (RAG), and side-by-side paper comparison — all with citations
back to the source text.

> **Status: Phase 2 — PDF Upload & Extraction.** Papers can now be uploaded,
> validated, saved, and have their text extracted page-by-page and stored in
> SQLite. NLP, embeddings, vector search, RAG, and LLM features are added in
> later phases.

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
- [ ] Phase 3 — NLP processing (section detection, NER, entity extraction)
- [ ] Phase 4 — Chunking + embeddings + FAISS index
- [ ] Phase 5 — Semantic search
- [ ] Phase 6 — RAG + question answering
- [ ] Phase 7 — Automatic structured summary
- [ ] Phase 8 — Paper comparison
- [ ] Phase 9 — Dashboard
- [ ] Phase 10 — Final polish, tests, docs
