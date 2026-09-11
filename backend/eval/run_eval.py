"""
Retrieval evaluation harness.

Computes Recall@k and Mean Reciprocal Rank (MRR) for retrieval_service.search
against a labeled QA set. Ground truth is page-number based: a retrieved
chunk "hits" if its page_number is one of the question's relevant_pages.

Usage:
    cd backend
    python eval/run_eval.py eval/qa_sets/fixture_paper.json
    python eval/run_eval.py eval/qa_sets/fixture_paper.json --k 1,3,5,10 --save

See eval/README.md for how to build a QA set for your own uploaded paper.
"""
import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal  # noqa: E402
from app.services import retrieval_service  # noqa: E402


def load_qa_set(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def evaluate(qa_set: dict, db, ks: list[int], use_hybrid: bool = False) -> dict:
    max_k = max(ks)
    per_question = []

    for item in qa_set["questions"]:
        # min_score=0.0: for evaluation we want the raw ranking, not the
        # production relevance threshold — otherwise a weak-but-correct
        # result would be silently dropped and look like a retrieval miss
        # when it was actually a threshold-tuning issue.
        if use_hybrid:
            results = retrieval_service.hybrid_search(
                query=item["question"], db=db, paper_id=qa_set["paper_id"], top_k=max_k,
            )
        else:
            results = retrieval_service.search(
                query=item["question"], db=db, paper_id=qa_set["paper_id"],
                top_k=max_k, min_score=0.0,
            )

        relevant_pages = set(item["relevant_pages"])
        first_hit_rank = None
        for rank, r in enumerate(results, start=1):
            if r.page_number in relevant_pages:
                first_hit_rank = rank
                break

        hits_at_k = {k: (first_hit_rank is not None and first_hit_rank <= k) for k in ks}
        reciprocal_rank = (1.0 / first_hit_rank) if first_hit_rank else 0.0

        per_question.append({
            "question": item["question"],
            "relevant_pages": item["relevant_pages"],
            "first_hit_rank": first_hit_rank,
            "reciprocal_rank": reciprocal_rank,
            "hits_at_k": hits_at_k,
            "retrieved_pages": [r.page_number for r in results[:max_k]],
        })

    n = len(per_question) or 1
    recall_at_k = {k: sum(q["hits_at_k"][k] for q in per_question) / n for k in ks}
    mrr = sum(q["reciprocal_rank"] for q in per_question) / n

    return {
        "paper_id": qa_set["paper_id"],
        "method": "hybrid" if use_hybrid else "vector",
        "n_questions": len(per_question),
        "recall_at_k": recall_at_k,
        "mrr": mrr,
        "per_question": per_question,
    }


def print_report(report: dict, ks: list[int]) -> None:
    print(f"\nEvaluated {report['n_questions']} questions against paper '{report['paper_id']}' (method: {report['method']})\n")
    print(f"{'Metric':<12}Value")
    print("-" * 24)
    for k in ks:
        print(f"Recall@{k:<5}{report['recall_at_k'][k]:.3f}")
    print(f"{'MRR':<12}{report['mrr']:.3f}")

    print("\nPer-question detail:")
    for q in report["per_question"]:
        status = f"rank {q['first_hit_rank']}" if q["first_hit_rank"] else "MISS"
        print(f"  [{status:>8}] {q['question']}")


def main():
    parser = argparse.ArgumentParser(description="Evaluate PaperMind's retrieval quality.")
    parser.add_argument("qa_set", help="Path to a QA set JSON file (see eval/qa_sets/)")
    parser.add_argument("--k", default="1,3,5,10", help="Comma-separated k values for Recall@k")
    parser.add_argument("--save", action="store_true", help="Save the full report to eval/results/")
    parser.add_argument("--hybrid", action="store_true", help="Evaluate hybrid (BM25 + vector) search instead of vector-only")
    args = parser.parse_args()

    ks = sorted(int(x) for x in args.k.split(","))
    qa_set = load_qa_set(args.qa_set)

    db = SessionLocal()
    try:
        report = evaluate(qa_set, db, ks, use_hybrid=args.hybrid)
    finally:
        db.close()

    print_report(report, ks)

    if args.save:
        results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
        os.makedirs(results_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(results_dir, f"{timestamp}_{report['paper_id']}_{report['method']}.json")
        with open(out_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nSaved full report to {out_path}")


if __name__ == "__main__":
    main()
