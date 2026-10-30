import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getSummary, regenerateSummary } from "../services/api.js";

const FIELD_LABELS = {
  research_problem: "Research Problem",
  objective: "Objective",
  methodology: "Methodology",
  models_algorithms: "Models / Algorithms",
  dataset: "Dataset",
  evaluation_metrics: "Evaluation Metrics",
  key_results: "Key Results",
  limitations: "Limitations",
  future_work: "Future Work",
};

function SummaryCard({ label, text }) {
  const unavailable = !text || text.toLowerCase().includes("not available");
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="mb-2 text-sm font-semibold text-slate-700">{label}</h3>
      <p className={`text-sm ${unavailable ? "text-slate-400 italic" : "text-slate-600"}`}>
        {text || "Not available in the paper."}
      </p>
    </div>
  );
}

export default function Summary() {
  const { paperId } = useParams();
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [regenerating, setRegenerating] = useState(false);
  const [error, setError] = useState("");

  const load = () => {
    setLoading(true);
    setError("");
    getSummary(paperId)
      .then(setSummary)
      .catch((err) => setError(err?.response?.data?.detail || "Could not generate summary."))
      .finally(() => setLoading(false));
  };

  useEffect(load, [paperId]);

  const handleRegenerate = async () => {
    setRegenerating(true);
    try {
      const data = await regenerateSummary(paperId);
      setSummary(data);
    } catch (err) {
      setError(err?.response?.data?.detail || "Could not regenerate summary.");
    } finally {
      setRegenerating(false);
    }
  };

  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <Link to={`/papers/${paperId}`} className="text-sm text-brand-600 hover:underline">
        ← Back to Paper
      </Link>

      <div className="mt-4 flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-800">Research Summary</h1>
        <button
          onClick={handleRegenerate}
          disabled={loading || regenerating}
          className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          {regenerating ? "Regenerating…" : "Regenerate"}
        </button>
      </div>

      {loading && <p className="mt-8 text-slate-400">Generating summary…</p>}

      {error && (
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {summary && !loading && (
        <>
          {summary.generation_mode === "extractive" && (
            <p className="mt-6 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
              The configured LLM is unavailable. These fields are extracted from the paper text.
            </p>
          )}
          <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-2">
            {Object.entries(FIELD_LABELS).map(([key, label]) => (
              <SummaryCard key={key} label={label} text={summary[key]} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
