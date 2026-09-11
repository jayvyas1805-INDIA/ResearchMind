import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listPapers } from "../services/api.js";
import StatusBadge from "../components/StatusBadge.jsx";

export default function Papers() {
  const [papers, setPapers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    listPapers()
      .then(setPapers)
      .catch(() => setError("Could not load papers. Is the backend running?"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-800">Papers</h1>
        <Link
          to="/upload"
          className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600"
        >
          + Upload Paper
        </Link>
      </div>

      {loading && <p className="mt-8 text-slate-400">Loading…</p>}
      {error && (
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>
      )}

      {!loading && !error && papers.length === 0 && (
        <div className="mt-8 rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center text-slate-400">
          No papers uploaded yet.
        </div>
      )}

      {!loading && !error && papers.length > 0 && (
        <div className="mt-6 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
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
              {papers.map((paper) => (
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
  );
}
