import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { listPapers, searchPaper } from "../services/api.js";

function ScoreBar({ score }) {
  const pct = Math.round(Math.min(Math.max(score, 0), 1) * 100);
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-slate-200">
        <div className="h-full rounded-full bg-brand-500" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-slate-500">{score.toFixed(2)}</span>
    </div>
  );
}

export default function Search() {
  const [searchParams] = useSearchParams();
  const preselectedPaperId = searchParams.get("paper");

  const [papers, setPapers] = useState([]);
  const [paperId, setPaperId] = useState("");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [hasSearched, setHasSearched] = useState(false);

  useEffect(() => {
    listPapers()
      .then((data) => {
        setPapers(data);
        const readyPapers = data.filter((p) => p.processing_status === "processed");
        if (preselectedPaperId && readyPapers.some((p) => p.id === preselectedPaperId)) {
          setPaperId(preselectedPaperId);
        } else if (readyPapers.length > 0) {
          setPaperId(readyPapers[0].id);
        }
      })
      .catch(() => setError("Could not load papers. Is the backend running?"));
  }, [preselectedPaperId]);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!paperId || !query.trim()) return;

    setLoading(true);
    setError("");
    setHasSearched(true);
    try {
      const data = await searchPaper(paperId, query.trim());
      setResults(data.results);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(detail || "Search failed. Please try again.");
      setResults(null);
    } finally {
      setLoading(false);
    }
  };

  const readyPapers = papers.filter((p) => p.processing_status === "processed");

  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <h1 className="text-2xl font-semibold text-slate-800">Search</h1>
      <p className="mt-2 text-slate-500">
        Ask a natural-language question about one of your papers — search is
        based on meaning, not just keyword matching.
      </p>

      {readyPapers.length === 0 && papers.length === 0 && !error && (
        <div className="mt-8 rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center text-slate-400">
          No papers available yet — upload one first.
        </div>
      )}

      {papers.length > 0 && readyPapers.length === 0 && (
        <div className="mt-8 rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center text-slate-400">
          No papers have finished processing yet — check back shortly.
        </div>
      )}

      {readyPapers.length > 0 && (
        <form onSubmit={handleSearch} className="mt-8 space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-600">
              Paper
            </label>
            <select
              value={paperId}
              onChange={(e) => setPaperId(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 focus:border-brand-500 focus:outline-none"
            >
              {readyPapers.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title || p.filename}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-slate-600">
              Query
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="e.g. Which dataset was used to evaluate the model?"
                className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 focus:border-brand-500 focus:outline-none"
              />
              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="rounded-lg bg-brand-500 px-5 py-2 text-sm font-medium text-white hover:bg-brand-600 disabled:opacity-50"
              >
                {loading ? "Searching…" : "Search"}
              </button>
            </div>
          </div>
        </form>
      )}

      {error && (
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {hasSearched && !loading && !error && results && results.length === 0 && (
        <div className="mt-8 rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-slate-400">
          No sufficiently relevant results found for that query.
        </div>
      )}

      {results && results.length > 0 && (
        <div className="mt-8 space-y-4">
          {results.map((r) => (
            <div
              key={r.chunk_id}
              className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
            >
              <div className="mb-2 flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs text-slate-400">
                  {r.page_number && <span>Page {r.page_number}</span>}
                  {r.section && (
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 capitalize text-slate-500">
                      {r.section.replace(/_/g, " ")}
                    </span>
                  )}
                </div>
                <ScoreBar score={r.similarity_score} />
              </div>
              <p className="text-sm text-slate-700">{r.text}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
