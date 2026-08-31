import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getPaper, analyzePaper } from "../services/api.js";
import StatusBadge from "../components/StatusBadge.jsx";

function EntityChips({ label, items }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="mb-4">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
        {label}
      </p>
      <div className="flex flex-wrap gap-2">
        {items.map((item) => (
          <span
            key={item}
            className="rounded-full bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700"
          >
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}

function SectionBlock({ title, text }) {
  if (!text) return null;
  return (
    <div className="mb-6">
      <h3 className="mb-1 text-sm font-semibold text-slate-700">{title}</h3>
      <p className="whitespace-pre-line text-sm text-slate-600">{text}</p>
    </div>
  );
}

export default function PaperDetail() {
  const { paperId } = useParams();
  const [paper, setPaper] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reanalyzing, setReanalyzing] = useState(false);

  const load = () => {
    setLoading(true);
    getPaper(paperId)
      .then(setPaper)
      .catch(() => setError("Could not load this paper."))
      .finally(() => setLoading(false));
  };

  useEffect(load, [paperId]);

  const handleReanalyze = async () => {
    setReanalyzing(true);
    try {
      const data = await analyzePaper(paperId);
      setPaper(data);
    } catch {
      setError("Re-analysis failed.");
    } finally {
      setReanalyzing(false);
    }
  };

  if (loading) return <div className="mx-auto max-w-4xl px-6 py-10 text-slate-400">Loading…</div>;
  if (error) return <div className="mx-auto max-w-4xl px-6 py-10 text-red-600">{error}</div>;
  if (!paper) return null;

  const entities = paper.entities || {};

  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <Link to="/" className="text-sm text-brand-600 hover:underline">
        ← Back to Dashboard
      </Link>

      <div className="mt-4 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">
            {paper.title || paper.filename}
          </h1>
          {paper.authors && <p className="mt-1 text-sm text-slate-500">{paper.authors}</p>}
        </div>
        <StatusBadge status={paper.processing_status} />
      </div>

      {paper.error_message && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {paper.error_message}
        </div>
      )}

      <button
        onClick={handleReanalyze}
        disabled={reanalyzing}
        className="mt-4 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
      >
        {reanalyzing ? "Re-analyzing…" : "Re-run NLP analysis"}
      </button>

      <div className="mt-8 grid grid-cols-1 gap-8 md:grid-cols-3">
        <div className="md:col-span-2">
          <SectionBlock title="Abstract" text={paper.abstract} />
          <SectionBlock title="Methodology" text={paper.methodology} />
          <SectionBlock title="Results" text={paper.results_section} />
          <SectionBlock title="Limitations" text={paper.limitations} />
          <SectionBlock title="Conclusion" text={paper.conclusion} />

          {!paper.abstract &&
            !paper.methodology &&
            !paper.results_section &&
            !paper.limitations &&
            !paper.conclusion && (
              <p className="text-sm text-slate-400">
                No sections were confidently detected in this paper. This can
                happen with non-standard formatting — the raw extracted text
                is still stored.
              </p>
            )}
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="mb-4 text-sm font-semibold text-slate-700">
            Extracted Entities
          </h3>
          <EntityChips label="Models" items={entities.models} />
          <EntityChips label="Datasets" items={entities.datasets} />
          <EntityChips label="Metrics" items={entities.metrics} />
          <EntityChips label="Methods" items={entities.methods} />
          <EntityChips label="Technologies" items={entities.technologies} />
          <EntityChips label="Organizations" items={entities.organizations} />
          <EntityChips label="People" items={entities.persons} />

          {Object.values(entities).every((v) => !v || v.length === 0) && (
            <p className="text-sm text-slate-400">No entities detected.</p>
          )}
        </div>
      </div>
    </div>
  );
}
