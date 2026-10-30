"""
Ablation study harness.

Runs the fixture paper + QA set through several chunking/embedding
configurations, each in a fully isolated in-memory FAISS index — this
NEVER touches the live app's database or persisted FAISS index, so it's
safe to run repeatedly without risk of corrupting real data.

Reports Recall@k and MRR per configuration so you can see which knobs
actually move retrieval quality, instead of guessing.

Usage:
    cd backend
    python eval/ablation.py
    python eval/ablation.py --save
    python eval/ablation.py --k 1,3,5

Note: comparing different embedding models downloads each one on first use
(the sentence-transformers cache handles this), so the first run can take
a while if you haven't used those models before.
"""
import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
import faiss  # noqa: E402

from app.services import chunking_service, nlp_service  # noqa: E402
from app.services.chunking_service import PageInput  # noqa: E402
from eval.seed_fixture_paper import PAGE_TEXTS  # noqa: E402

QA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qa_sets", "fixture_paper.json")

# Each experiment varies exactly one thing from the "current default" row,
# so the effect of that one change is directly attributable.
DEFAULT_EXPERIMENTS = [
    {"label": "chunk=100 words (smaller)", "chunk_target_words": 100, "chunk_min_words": 20, "embedding_model": "all-MiniLM-L6-v2"},
    {"label": "chunk=180 words (current default)", "chunk_target_words": 180, "chunk_min_words": 40, "embedding_model": "all-MiniLM-L6-v2"},
    {"label": "chunk=300 words (larger)", "chunk_target_words": 300, "chunk_min_words": 60, "embedding_model": "all-MiniLM-L6-v2"},
    {"label": "larger embedding model (all-mpnet-base-v2)", "chunk_target_words": 180, "chunk_min_words": 40, "embedding_model": "all-mpnet-base-v2"},
]


def _embed(texts: list[str], model_name: str) -> np.ndarray:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(model_name)  # sentence-transformers caches this internally per process
    return model.encode(texts, normalize_embeddings=True, convert_to_numpy=True).astype("float32")


def run_experiment(chunk_target_words: int, chunk_min_words: int, embedding_model: str,
                    top_k_values: list[int], qa_questions: list[dict]) -> dict:
    """Runs one full configuration end-to-end in an isolated in-memory index."""
    full_text = "\n\n".join(PAGE_TEXTS[p] for p in sorted(PAGE_TEXTS))
    sections = nlp_service.detect_sections(nlp_service.clean_text(full_text))
    pages = [PageInput(page_number=p, text=nlp_service.clean_text(t)) for p, t in PAGE_TEXTS.items()]

    chunks = chunking_service.chunk_paper(
        pages, sections, target_words=chunk_target_words, min_words=chunk_min_words
    )
    if not chunks:
        raise RuntimeError("No chunks produced for this configuration.")

    texts = [c.text for c in chunks]
    vectors = _embed(texts, embedding_model)

    # Isolated, in-memory FAISS index — separate from the app's persisted one.
    dim = vectors.shape[1]
    index = faiss.IndexIDMap2(faiss.IndexFlatIP(dim))
    ids = np.arange(len(chunks), dtype="int64")
    index.add_with_ids(vectors, ids)
    id_to_chunk = {i: c for i, c in zip(ids, chunks)}

    def search(query: str, k: int):
        qvec = _embed([query], embedding_model)[0].reshape(1, -1)
        distances, result_ids = index.search(qvec, k)
        return [
            (id_to_chunk[cid], float(score))
            for cid, score in zip(result_ids[0], distances[0])
            if cid != -1
        ]

    max_k = max(top_k_values)
    recall_hits = {k: 0 for k in top_k_values}
    reciprocal_ranks = []

    for item in qa_questions:
        results = search(item["question"], max_k)
        relevant_pages = set(item["relevant_pages"])

        first_hit_rank = None
        for rank, (chunk, _score) in enumerate(results, start=1):
            if chunk.page_number in relevant_pages:
                first_hit_rank = rank
                break

        reciprocal_ranks.append(1.0 / first_hit_rank if first_hit_rank else 0.0)
        for k in top_k_values:
            if first_hit_rank and first_hit_rank <= k:
                recall_hits[k] += 1

    n = len(qa_questions)
    return {
        "chunk_target_words": chunk_target_words,
        "chunk_min_words": chunk_min_words,
        "embedding_model": embedding_model,
        "n_chunks": len(chunks),
        "recall_at_k": {k: recall_hits[k] / n for k in top_k_values},
        "mrr": sum(reciprocal_ranks) / n,
    }


def print_comparison_table(reports: list[dict], top_k_values: list[int]) -> None:
    headers = ["Experiment", "Chunks"] + [f"Recall@{k}" for k in top_k_values] + ["MRR"]
    col_widths = [40, 8] + [10] * len(top_k_values) + [6]

    def fmt_row(cells):
        return " | ".join(str(c).ljust(w) for c, w in zip(cells, col_widths))

    print("\n" + fmt_row(headers))
    print("-" * (sum(col_widths) + 3 * (len(col_widths) - 1)))
    for r in reports:
        row = [r["label"], r["n_chunks"]] + [f"{r['recall_at_k'][k]:.2f}" for k in top_k_values] + [f"{r['mrr']:.2f}"]
        print(fmt_row(row))


def main():
    parser = argparse.ArgumentParser(description="Run an ablation study over chunking/embedding configurations.")
    parser.add_argument("--k", default="1,3,5,10", help="Comma-separated k values for Recall@k")
    parser.add_argument("--save", action="store_true", help="Save results + a markdown write-up to eval/results/")
    args = parser.parse_args()

    top_k_values = sorted(int(x) for x in args.k.split(","))

    with open(QA_PATH) as f:
        qa_set = json.load(f)
    qa_questions = qa_set["questions"]

    print(f"Running {len(DEFAULT_EXPERIMENTS)} experiments against the fixture paper ({len(qa_questions)} questions)...")

    reports = []
    for exp in DEFAULT_EXPERIMENTS:
        print(f"-> {exp['label']} ...", end=" ", flush=True)
        try:
            report = run_experiment(
                exp["chunk_target_words"], exp["chunk_min_words"], exp["embedding_model"],
                top_k_values, qa_questions,
            )
            report["label"] = exp["label"]
            reports.append(report)
            print("done")
        except Exception as exc:
            print(f"FAILED: {exc}")

    print_comparison_table(reports, top_k_values)

    if args.save:
        results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
        os.makedirs(results_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        json_path = os.path.join(results_dir, f"{timestamp}_ablation.json")
        with open(json_path, "w") as f:
            json.dump(reports, f, indent=2)

        md_path = os.path.join(results_dir, f"{timestamp}_ablation.md")
        with open(md_path, "w") as f:
            f.write(f"# Ablation Study — {timestamp}\n\n")
            f.write(f"Fixture paper, {len(qa_questions)} questions.\n\n")
            headers = ["Experiment", "Chunks"] + [f"Recall@{k}" for k in top_k_values] + ["MRR"]
            f.write("| " + " | ".join(headers) + " |\n")
            f.write("|" + "---|" * len(headers) + "\n")
            for r in reports:
                row = [r["label"], str(r["n_chunks"])] + [f"{r['recall_at_k'][k]:.2f}" for k in top_k_values] + [f"{r['mrr']:.2f}"]
                f.write("| " + " | ".join(row) + " |\n")
            f.write("\n## Notes\n\n_Add your interpretation of each result here before including this in a report._\n")

        print(f"\nSaved to {json_path}\nSaved write-up template to {md_path}")


if __name__ == "__main__":
    main()
