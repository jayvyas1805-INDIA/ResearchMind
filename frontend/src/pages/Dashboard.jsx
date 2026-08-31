import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listPapers } from "../services/api.js";
import StatusBadge from "../components/StatusBadge.jsx";

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
  const pending = total - processed;

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <h1 className="text-2xl font-semibold text-slate-800">Dashboard</h1>
      <p className="mt-2 text-slate-500">
        Your uploaded papers and processing status appear here.
      </p>

      <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-sm text-slate-500">Total Papers</p>
          <p className="mt-1 text-2xl font-semibold text-slate-800">{total}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-sm text-slate-500">Processed</p>
          <p className="mt-1 text-2xl font-semibold text-slate-800">{processed}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-sm text-slate-500">Pending</p>
          <p className="mt-1 text-2xl font-semibold text-slate-800">{pending}</p>
        </div>
      </div>

      <div className="mt-10">
        {loading && <p className="text-slate-400">Loading papers…</p>}

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {!loading && !error && papers.length === 0 && (
          <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center text-slate-400">
            No papers uploaded yet — head to the Upload page to add your first
            paper.
          </div>
        )}

        {!loading && !error && papers.length > 0 && (
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
                {papers.map((paper) => (
                  <tr
                    key={paper.id}
                    className="border-t border-slate-100 hover:bg-slate-50"
                  >
                    <td className="px-4 py-3 text-slate-700">
                      <Link
                        to={`/papers/${paper.id}`}
                        className="font-medium text-brand-600 hover:underline"
                      >
                        {paper.title || paper.filename}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-slate-700">{paper.page_count}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={paper.processing_status} />
                    </td>
                    <td className="px-4 py-3 text-slate-500">
                      {paper.upload_date
                        ? new Date(paper.upload_date).toLocaleString()
                        : "—"}
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
