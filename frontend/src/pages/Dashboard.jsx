import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listPapers } from "../services/api.js";
import StatusBadge from "../components/StatusBadge.jsx";

const QUICK_ACTIONS = [
  { to: "/upload", label: "Upload a Paper" },
  { to: "/search", label: "Search a Paper" },
  { to: "/chat", label: "Ask a Question" },
  { to: "/compare", label: "Compare Papers" },
];

export default function Dashboard() {
  const [papers, setPapers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    listPapers()
      .then(setPapers)
      .catch(() => setError("Could not load papers. Is the backend running?"))
      .finally(() => setLoading(false));
  }, []);

  const total = papers.length;
  const processed = papers.filter((p) => p.processing_status === "processed").length;
  const pending = papers.filter((p) => p.processing_status === "processing" || p.processing_status === "uploaded").length;
  const failed = papers.filter((p) => p.processing_status === "failed").length;
  const recent = [...papers]
    .sort((a, b) => new Date(b.upload_date) - new Date(a.upload_date))
    .slice(0, 5);

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <h1 className="text-2xl font-semibold text-slate-800">Dashboard</h1>
      <p className="mt-2 text-slate-500">Overview of your research paper library.</p>

      <div className="mt-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          { label: "Total Papers", value: total },
          { label: "Processed", value: processed },
          { label: "Pending", value: pending },
          { label: "Failed", value: failed },
        ].map((stat) => (
          <div key={stat.label} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm text-slate-500">{stat.label}</p>
            <p className="mt-1 text-2xl font-semibold text-slate-800">{stat.value}</p>
          </div>
        ))}
      </div>

      <div className="mt-8 flex flex-wrap gap-3">
        {QUICK_ACTIONS.map((action) => (
          <Link
            key={action.to}
            to={action.to}
            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            {action.label}
          </Link>
        ))}
      </div>

      <div className="mt-10">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-800">Recently Uploaded</h2>
          {papers.length > 5 && (
            <Link to="/papers" className="text-sm text-brand-600 hover:underline">
              View all →
            </Link>
          )}
        </div>

        {loading && <p className="text-slate-400">Loading…</p>}
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>
        )}
        {!loading && !error && recent.length === 0 && (
          <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center text-slate-400">
            No papers uploaded yet — head to Upload to add your first paper.
          </div>
        )}
        {!loading && !error && recent.length > 0 && (
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Filename</th>
                  <th className="px-4 py-3 font-medium">Pages</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Uploaded</th>
                </tr>
              </thead>
              <tbody>
                {recent.map((paper) => (
                  <tr key={paper.id} className="border-t border-slate-100 hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <Link to={`/papers/${paper.id}`} className="font-medium text-brand-600 hover:underline">
                        {paper.title || paper.filename}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-slate-700">{paper.page_count}</td>
                    <td className="px-4 py-3"><StatusBadge status={paper.processing_status} /></td>
                    <td className="px-4 py-3 text-slate-500">
                      {paper.upload_date ? new Date(paper.upload_date).toLocaleString() : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
