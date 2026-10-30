import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getPaper, analyzePaper, getSummary, searchPaper, askPaper } from "../services/api.js";
import StatusBadge from "../components/StatusBadge.jsx";

const TABS = ["Overview", "Summary", "Search", "Ask"];

function EntityChips({ label, items }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="mb-4">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">{label}</p>
      <div className="flex flex-wrap gap-2">
        {items.map((item) => (
          <span key={item} className="rounded-full bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700">
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

function OverviewTab({ paper, onReanalyze, reanalyzing }) {
  const entities = paper.entities || {};
  return (
    <div>
      {paper.error_message && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {paper.error_message}
        </div>
      )}
      <button
        onClick={onReanalyze}
        disabled={reanalyzing}
        className="mb-6 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
      >
        {reanalyzing ? "Re-analyzing…" : "Re-run NLP analysis"}
      </button>
      <div className="grid grid-cols-1 gap-8 md:grid-cols-3">
        <div className="md:col-span-2">
          <SectionBlock title="Abstract" text={paper.abstract} />
          <SectionBlock title="Methodology" text={paper.methodology} />
          <SectionBlock title="Results" text={paper.results_section} />
          <SectionBlock title="Limitations" text={paper.limitations} />
          <SectionBlock title="Conclusion" text={paper.conclusion} />
          {!paper.abstract && !paper.methodology && !paper.results_section && (
            <p className="text-sm text-slate-400">No sections were confidently detected in this paper.</p>
          )}
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h3 className="mb-4 text-sm font-semibold text-slate-700">Extracted Entities</h3>
          <EntityChips label="Models" items={entities.models} />
          <EntityChips label="Datasets" items={entities.datasets} />
          <EntityChips label="Metrics" items={entities.metrics} />
          <EntityChips label="Methods" items={entities.methods} />
          <EntityChips label="Technologies" items={entities.technologies} />
          {Object.values(entities).every((v) => !v || v.length === 0) && (
            <p className="text-sm text-slate-400">No entities detected.</p>
          )}
        </div>
      </div>
    </div>
  );
}

const SUMMARY_LABELS = {
  research_problem: "Research Problem", objective: "Objective", methodology: "Methodology",
  models_algorithms: "Models / Algorithms", dataset: "Dataset", evaluation_metrics: "Evaluation Metrics",
  key_results: "Key Results", limitations: "Limitations", future_work: "Future Work",
};

function SummaryTab({ paperId }) {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getSummary(paperId).then(setSummary).catch(() => setError("Could not generate summary.")).finally(() => setLoading(false));
  }, [paperId]);

  if (loading) return <p className="text-slate-400">Generating summary…</p>;
  if (error) return <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>;
  if (!summary) return null;

  return (
    <>
      {summary.generation_mode === "extractive" && (
        <p className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          The configured LLM is unavailable. These fields are extracted from the paper text.
        </p>
      )}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {Object.entries(SUMMARY_LABELS).map(([key, label]) => (
          <div key={key} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="mb-2 text-sm font-semibold text-slate-700">{label}</h3>
            <p className="text-sm text-slate-600">{summary[key]}</p>
          </div>
        ))}
      </div>
    </>
  );
}

function SearchTab({ paperId }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError("");
    setResults(null);
    try {
      const data = await searchPaper(paperId, query.trim(), null, true);
      setResults(data.results);
    } catch (err) {
      setError(err?.response?.data?.detail || "Search failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <form onSubmit={handleSearch} className="mb-6 flex gap-2">
        <input
          type="text" value={query} onChange={(e) => setQuery(e.target.value)}
          placeholder="Search within this paper…"
          className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
        />
        <button type="submit" disabled={loading} className="rounded-lg bg-brand-500 px-5 py-2 text-sm font-medium text-white hover:bg-brand-600 disabled:opacity-50">
          {loading ? "…" : "Search"}
        </button>
      </form>
      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
      {results && results.length === 0 && <p className="text-sm text-slate-400">No relevant results found.</p>}
      {results && results.map((r) => (
        <div key={r.chunk_id} className="mb-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="mb-1 text-xs text-slate-400">
            {r.page_number ? `Page ${r.page_number}` : ""} {r.section ? `· ${r.section.replace(/_/g, " ")}` : ""}
          </p>
          <p className="text-sm font-medium leading-6 text-slate-800">{r.excerpt || r.text}</p>
          {r.excerpt && r.excerpt !== r.text && (
            <details className="mt-3">
              <summary className="cursor-pointer text-xs font-medium text-brand-600">Show full passage</summary>
              <p className="mt-2 whitespace-pre-line text-sm text-slate-600">{r.text}</p>
            </details>
          )}
        </div>
      ))}
    </div>
  );
}

function GroundednessBadge({ isGrounded, supportedRatio, sentenceGrounding }) {
  const [expanded, setExpanded] = useState(false);
  if (isGrounded === null || isGrounded === undefined) return null;

  const pct = Math.round((supportedRatio || 0) * 100);
  return (
    <div className="mt-2 text-left">
      <button
        onClick={() => setExpanded((v) => !v)}
        className={`rounded-full px-2.5 py-1 text-xs font-medium ${isGrounded ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}
      >
        {isGrounded ? "✓ Grounded" : "⚠ Possibly ungrounded"} ({pct}% of sentences supported)
      </button>
      {expanded && sentenceGrounding && (
        <div className="mt-2 space-y-1 rounded-lg border border-slate-200 bg-slate-50 p-2">
          {sentenceGrounding.map((s, i) => (
            <div key={i} className="text-xs text-slate-500">
              <span className={s.support_score >= 0.5 ? "text-emerald-600" : "text-amber-600"}>
                [{s.support_score.toFixed(2)}]
              </span>{" "}
              {s.sentence}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function AskTab({ paperId }) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleAsk = async (e) => {
    e.preventDefault();
    if (!question.trim() || loading) return;
    const q = question.trim();
    setMessages((m) => [...m, { role: "user", text: q }]);
    setQuestion("");
    setLoading(true);
    setError("");
    try {
      const data = await askPaper(paperId, q);
      setMessages((m) => [...m, {
        role: "assistant", text: data.answer, sources: data.sources,
        answerMode: data.answer_mode,
        isGrounded: data.is_grounded, supportedRatio: data.supported_ratio,
        sentenceGrounding: data.sentence_grounding,
      }]);
    } catch (err) {
      setError(err?.response?.data?.detail || "Something went wrong answering that question.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="mb-4 space-y-3">
        {messages.length === 0 && <p className="text-sm text-slate-400">Ask a question about this paper.</p>}
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-right" : ""}>
            <div className={`inline-block max-w-[85%] rounded-xl px-4 py-2 text-sm ${m.role === "user" ? "bg-brand-500 text-white" : "border border-slate-200 bg-white text-slate-700"}`}>
              {m.text}
            </div>
            {m.role === "assistant" && (
              <>
                {m.answerMode === "extractive" && (
                  <p className="mt-2 text-xs text-amber-700">
                    Extracted directly from matching paper passages because the configured LLM is unavailable.
                  </p>
                )}
                <GroundednessBadge isGrounded={m.isGrounded} supportedRatio={m.supportedRatio} sentenceGrounding={m.sentenceGrounding} />
              </>
            )}
            {m.sources && m.sources.length > 0 && (
              <div className="mt-2 space-y-1 text-left">
                {m.sources.map((s) => (
                  <div key={s.chunk_id} className="rounded-lg bg-slate-100 px-3 py-1.5 text-xs text-slate-500">
                    {s.page_number ? `Page ${s.page_number}` : "Unknown page"} — {s.text.slice(0, 140)}{s.text.length > 140 ? "…" : ""}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
        {loading && <p className="text-sm text-slate-400">Thinking…</p>}
      </div>
      {error && (
        <p className="mb-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>
      )}
      <form onSubmit={handleAsk} className="flex gap-2">
        <input
          type="text" value={question} onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question…"
          className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
        />
        <button type="submit" disabled={loading} className="rounded-lg bg-brand-500 px-5 py-2 text-sm font-medium text-white hover:bg-brand-600 disabled:opacity-50">
          Ask
        </button>
      </form>
    </div>
  );
}

export default function PaperDetail() {
  const { paperId } = useParams();
  const [paper, setPaper] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reanalyzing, setReanalyzing] = useState(false);
  const [tab, setTab] = useState("Overview");

  const load = () => {
    setLoading(true);
    getPaper(paperId).then(setPaper).catch(() => setError("Could not load this paper.")).finally(() => setLoading(false));
  };
  useEffect(load, [paperId]);

  const handleReanalyze = async () => {
    setReanalyzing(true);
    try {
      const data = await analyzePaper(paperId);
      setPaper(data);
    } finally {
      setReanalyzing(false);
    }
  };

  if (loading) return <div className="mx-auto max-w-4xl px-6 py-10 text-slate-400">Loading…</div>;
  if (error) return <div className="mx-auto max-w-4xl px-6 py-10 text-red-600">{error}</div>;
  if (!paper) return null;

  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <Link to="/papers" className="text-sm text-brand-600 hover:underline">← Back to Papers</Link>

      <div className="mt-4 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">{paper.title || paper.filename}</h1>
          {paper.authors && <p className="mt-1 text-sm text-slate-500">{paper.authors}</p>}
        </div>
        <StatusBadge status={paper.processing_status} />
      </div>

      <div className="mt-6 flex gap-6 border-b border-slate-200">
        {TABS.map((t) => (
          <button
            key={t} onClick={() => setTab(t)}
            className={`border-b-2 pb-2 text-sm font-medium ${tab === t ? "border-brand-500 text-brand-600" : "border-transparent text-slate-500 hover:text-slate-800"}`}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {tab === "Overview" && <OverviewTab paper={paper} onReanalyze={handleReanalyze} reanalyzing={reanalyzing} />}
        {tab === "Summary" && <SummaryTab paperId={paperId} />}
        {tab === "Search" && <SearchTab paperId={paperId} />}
        {tab === "Ask" && <AskTab paperId={paperId} />}
      </div>
    </div>
  );
}
