import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { listPapers, askPaper } from "../services/api.js";

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

export default function Chat() {
  const [searchParams] = useSearchParams();
  const preselected = searchParams.get("paper");

  const [papers, setPapers] = useState([]);
  const [paperId, setPaperId] = useState("");
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]); // {role, text, sources?}
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    listPapers()
      .then((data) => {
        setPapers(data);
        const ready = data.filter((p) => p.processing_status === "processed");
        if (preselected && ready.some((p) => p.id === preselected)) setPaperId(preselected);
        else if (ready.length > 0) setPaperId(ready[0].id);
      })
      .catch(() => setError("Could not load papers. Is the backend running?"));
  }, [preselected]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleAsk = async (e) => {
    e.preventDefault();
    if (!paperId || !question.trim() || loading) return;

    const q = question.trim();
    setMessages((m) => [...m, { role: "user", text: q }]);
    setQuestion("");
    setLoading(true);
    setError("");

    try {
      const data = await askPaper(paperId, q);
      setMessages((m) => [...m, {
        role: "assistant", text: data.answer, sources: data.sources,
        isGrounded: data.is_grounded, supportedRatio: data.supported_ratio,
        sentenceGrounding: data.sentence_grounding,
      }]);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(detail || "Something went wrong answering that question.");
    } finally {
      setLoading(false);
    }
  };

  const readyPapers = papers.filter((p) => p.processing_status === "processed");

  return (
    <div className="mx-auto flex max-w-3xl flex-col px-6 py-10" style={{ minHeight: "calc(100vh - 65px)" }}>
      <h1 className="text-2xl font-semibold text-slate-800">Ask a Paper</h1>
      <p className="mt-2 text-slate-500">
        Ask questions in plain English — answers are grounded in the paper's
        content, with sources shown below each answer.
      </p>

      {readyPapers.length > 0 && (
        <select
          value={paperId}
          onChange={(e) => {
            setPaperId(e.target.value);
            setMessages([]);
          }}
          className="mt-4 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 focus:border-brand-500 focus:outline-none"
        >
          {readyPapers.map((p) => (
            <option key={p.id} value={p.id}>
              {p.title || p.filename}
            </option>
          ))}
        </select>
      )}

      {papers.length > 0 && readyPapers.length === 0 && (
        <div className="mt-8 rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center text-slate-400">
          No papers have finished processing yet.
        </div>
      )}

      <div className="mt-6 flex-1 space-y-4 overflow-y-auto">
        {messages.length === 0 && (
          <p className="text-sm text-slate-400">
            Try: "What dataset was used?" or "What are the key results?"
          </p>
        )}

        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-right" : ""}>
            <div
              className={`inline-block max-w-[85%] rounded-xl px-4 py-2 text-sm ${
                m.role === "user"
                  ? "bg-brand-500 text-white"
                  : "border border-slate-200 bg-white text-slate-700"
              }`}
            >
              {m.text}
            </div>
            {m.role === "assistant" && (
              <GroundednessBadge isGrounded={m.isGrounded} supportedRatio={m.supportedRatio} sentenceGrounding={m.sentenceGrounding} />
            )}
            {m.sources && m.sources.length > 0 && (
              <div className="mt-2 space-y-1 text-left">
                {m.sources.map((s) => (
                  <div key={s.chunk_id} className="rounded-lg bg-slate-100 px-3 py-1.5 text-xs text-slate-500">
                    <span className="font-medium">
                      {s.page_number ? `Page ${s.page_number}` : "Unknown page"}
                      {s.section ? ` · ${s.section.replace(/_/g, " ")}` : ""}
                    </span>{" "}
                    — {s.text.slice(0, 140)}
                    {s.text.length > 140 ? "…" : ""}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
        {loading && <p className="text-sm text-slate-400">Thinking…</p>}
        <div ref={bottomRef} />
      </div>

      {error && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {readyPapers.length > 0 && (
        <form onSubmit={handleAsk} className="mt-4 flex gap-2">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask a question about this paper…"
            className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700 focus:border-brand-500 focus:outline-none"
          />
          <button
            type="submit"
            disabled={loading || !question.trim()}
            className="rounded-lg bg-brand-500 px-5 py-2 text-sm font-medium text-white hover:bg-brand-600 disabled:opacity-50"
          >
            Ask
          </button>
        </form>
      )}
    </div>
  );
}
