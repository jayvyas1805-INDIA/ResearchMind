import { useEffect, useState, Fragment } from "react";
import { Link } from "react-router-dom";
import { getLeaderboard, getLeaderboardFacets } from "../services/api.js";

export default function Leaderboard() {
  const [facets, setFacets] = useState({ models: [], datasets: [], metrics: [] });
  const [dataset, setDataset] = useState("");
  const [metric, setMetric] = useState("");
  const [model, setModel] = useState("");
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expandedId, setExpandedId] = useState(null);

  useEffect(() => {
    getLeaderboardFacets().then(setFacets).catch(() => {});
  }, []);

  const runQuery = () => {
    setLoading(true);
    setError("");
    getLeaderboard({ dataset, metric, model })
      .then((data) => setEntries(data.entries))
      .catch(() => setError("Could not load the leaderboard. Is the backend running?"))
      .finally(() => setLoading(false));
  };

  useEffect(runQuery, []); // initial load, unfiltered

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <h1 className="text-2xl font-semibold text-slate-800">Results Leaderboard</h1>
      <p className="mt-2 text-slate-500">
        Structured numeric results extracted across every paper you've uploaded —
        not regenerated per query, a persistent table that grows as your library grows.
      </p>

      <div className="mt-6 flex flex-wrap items-end gap-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500">Dataset</label>
          <select value={dataset} onChange={(e) => setDataset(e.target.value)} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700">
            <option value="">Any</option>
            {facets.datasets.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500">Metric</label>
          <select value={metric} onChange={(e) => setMetric(e.target.value)} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700">
            <option value="">Any</option>
            {facets.metrics.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-500">Model</label>
          <select value={model} onChange={(e) => setModel(e.target.value)} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700">
            <option value="">Any</option>
            {facets.models.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>
        <button onClick={runQuery} className="rounded-lg bg-brand-500 px-5 py-2 text-sm font-medium text-white hover:bg-brand-600">
          Apply Filters
        </button>
      </div>

      {loading && <p className="mt-8 text-slate-400">Loading…</p>}
      {error && <div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>}

      {!loading && !error && entries.length === 0 && (
        <div className="mt-8 rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center text-slate-400">
          No matching results found. Upload more papers, or try different filters — extraction only
          catches results phrased with a metric name near a number in the same sentence.
        </div>
      )}

      {!loading && entries.length > 0 && (
        <div className="mt-6 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">Value</th>
                <th className="px-4 py-3 font-medium">Metric</th>
                <th className="px-4 py-3 font-medium">Model</th>
                <th className="px-4 py-3 font-medium">Dataset</th>
                <th className="px-4 py-3 font-medium">Paper</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => (
                <Fragment key={e.id}>
                  <tr
                    className="cursor-pointer border-t border-slate-100 hover:bg-slate-50"
                    onClick={() => setExpandedId(expandedId === e.id ? null : e.id)}
                  >
                    <td className="px-4 py-3 font-semibold text-slate-800">{e.value_text}</td>
                    <td className="px-4 py-3 text-slate-700">{e.metric_name}</td>
                    <td className="px-4 py-3 text-slate-700">{e.model_name || "—"}</td>
                    <td className="px-4 py-3 text-slate-700">{e.dataset_name || "—"}</td>
                    <td className="px-4 py-3">
                      <Link to={`/papers/${e.paper_id}`} className="text-brand-600 hover:underline" onClick={(ev) => ev.stopPropagation()}>
                        {e.paper_title}
                      </Link>
                    </td>
                  </tr>
                  {expandedId === e.id && (
                    <tr className="border-t border-slate-100 bg-slate-50">
                      <td colSpan={5} className="px-4 py-3 text-xs text-slate-500">
                        {e.page_number ? `Page ${e.page_number} — ` : ""}"{e.sentence}"
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
