import { useEffect, useState } from "react";
import { listPapers, comparePapers } from "../services/api.js";

function InfoRow({ label, value }) {
  return (
    <div className="mb-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-0.5 text-sm text-slate-700">{value}</p>
    </div>
  );
}

function PaperColumn({ brief }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="mb-4 text-base font-semibold text-slate-800">{brief.title}</h3>
      <InfoRow label="Methodology" value={brief.methodology} />
      <InfoRow label="Dataset(s)" value={brief.dataset} />
      <InfoRow label="Model(s)" value={brief.models} />
      <InfoRow label="Metric(s)" value={brief.metrics} />
      <InfoRow label="Results" value={brief.results} />
      <InfoRow label="Limitations" value={brief.limitations} />
    </div>
  );
}

function ComparisonBlock({ title, text }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="mb-2 text-sm font-semibold text-slate-700">{title}</h3>
      <p className="text-sm text-slate-600">{text}</p>
    </div>
  );
}

export default function Compare() {
  const [papers, setPapers] = useState([]);
  const [id1, setId1] = useState("");
  const [id2, setId2] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    listPapers()
      .then((data) => {
        const ready = data.filter((p) => p.processing_status === "processed");
        setPapers(ready);
        if (ready.length > 0) setId1(ready[0].id);
        if (ready.length > 1) setId2(ready[1].id);
      })
      .catch(() => setError("Could not load papers. Is the backend running?"));
  }, []);

  const handleCompare = async () => {
    if (!id1 || !id2 || id1 === id2) {
      setError("Please select two different papers.");
      return;
    }
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = await comparePapers(id1, id2);
      setResult(data);
    } catch (err) {
      setError(err?.response?.data?.detail || "Comparison failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <h1 className="text-2xl font-semibold text-slate-800">Compare Papers</h1>
      <p className="mt-2 text-slate-500">
        Select two processed papers to compare their methodology, datasets,
        models, results, and more.
      </p>

      {papers.length < 2 && (
        <div className="mt-8 rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center text-slate-400">
          Upload and process at least two papers to compare them.
        </div>
      )}

      {papers.length >= 2 && (
        <div className="mt-6 flex flex-col gap-4 sm:flex-row sm:items-end">
          <div className="flex-1">
            <label className="mb-1 block text-sm font-medium text-slate-600">Paper A</label>
            <select
              value={id1}
              onChange={(e) => setId1(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 focus:border-brand-500 focus:outline-none"
            >
              {papers.map((p) => (
                <option key={p.id} value={p.id}>{p.title || p.filename}</option>
              ))}
            </select>
          </div>
          <div className="flex-1">
            <label className="mb-1 block text-sm font-medium text-slate-600">Paper B</label>
            <select
              value={id2}
              onChange={(e) => setId2(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 focus:border-brand-500 focus:outline-none"
            >
              {papers.map((p) => (
                <option key={p.id} value={p.id}>{p.title || p.filename}</option>
              ))}
            </select>
          </div>
          <button
            onClick={handleCompare}
            disabled={loading}
            className="rounded-lg bg-brand-500 px-5 py-2 text-sm font-medium text-white hover:bg-brand-600 disabled:opacity-50"
          >
            {loading ? "Comparing…" : "Compare"}
          </button>
        </div>
      )}

      {error && (
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {result && (
        <>
          {result.generation_mode === "extractive" && (
            <p className="mt-6 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
              The configured LLM is unavailable. This comparison uses fields extracted from each paper.
            </p>
          )}
          <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-2">
            <PaperColumn brief={result.paper1} />
            <PaperColumn brief={result.paper2} />
          </div>

          <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-2">
            <ComparisonBlock title="Similarities" text={result.similarities} />
            <ComparisonBlock title="Differences" text={result.differences} />
            <ComparisonBlock title="Methodology Comparison" text={result.methodology_comparison} />
            <ComparisonBlock title="Dataset Comparison" text={result.dataset_comparison} />
            <ComparisonBlock title="Model Comparison" text={result.model_comparison} />
            <ComparisonBlock title="Result Comparison" text={result.result_comparison} />
          </div>
        </>
      )}
    </div>
  );
}
