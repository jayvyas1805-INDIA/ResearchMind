# PaperMind

**NLP & LLM-Powered Research Paper Intelligence Engine**

Upload research papers (PDF) and get structured summaries, semantic search,
grounded Q&A (RAG), and side-by-side paper comparison — all with citations
back to the source text.

> **Status: Phase 1 — Project Setup.** This phase only sets up the skeleton
> (backend health check + frontend shell). PDF processing, NLP, embeddings,
> vector search, RAG, and LLM features are added in later phases.

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

- Python 3.10+
- Node.js 18+
- (Later phases) [Ollama](https://ollama.com) installed locally, since the
  default LLM provider is a local open-source model.

---

## Backend — Setup & Run

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # edit values if needed
python -m uvicorn app.main:app --reload --port 8000
```

Backend will be running at: **http://localhost:8000**
Interactive API docs: **http://localhost:8000/docs**

### Endpoint to test (Phase 1)

```
GET http://localhost:8000/api/health
```

Expected response:

```json
{ "status": "ok", "app": "PaperMind", "environment": "development" }
```

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
| `VITE_API_BASE_URL` | Backend API base URL | `http://localhost:8000/api` |

**No secrets are hardcoded anywhere in the codebase** — everything sensitive
is read from environment variables.

---

## Roadmap (implemented phase by phase)

- [x] Phase 1 — Project setup
- [ ] Phase 2 — PDF upload & extraction
- [ ] Phase 3 — NLP processing (section detection, NER, entity extraction)
- [ ] Phase 4 — Chunking + embeddings + FAISS index
- [ ] Phase 5 — Semantic search
- [ ] Phase 6 — RAG + question answering
- [ ] Phase 7 — Automatic structured summary
- [ ] Phase 8 — Paper comparison
- [ ] Phase 9 — Dashboard
- [ ] Phase 10 — Final polish, tests, docs
