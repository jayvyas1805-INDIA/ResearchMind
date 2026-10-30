import { useEffect, useState } from "react";
import { getSettings } from "../services/api.js";

const LABELS = {
  app_name: "App Name",
  environment: "Environment",
  embedding_model: "Embedding Model",
  chunk_target_words: "Chunk Target (words)",
  default_top_k: "Default Search Results",
  min_similarity_threshold: "Min Similarity Threshold",
  llm_provider: "LLM Provider",
  llm_model: "LLM Model",
  max_upload_size_mb: "Max Upload Size (MB)",
};

export default function Settings() {
  const [settings, setSettings] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getSettings()
      .then(setSettings)
      .catch(() => setError("Could not load settings. Is the backend running?"));
  }, []);

  return (
    <div className="mx-auto max-w-2xl px-6 py-10">
      <h1 className="text-2xl font-semibold text-slate-800">Settings</h1>
      <p className="mt-2 text-slate-500">
        Current backend configuration (read-only). Change values via the
        backend's <code className="rounded bg-slate-100 px-1">.env</code> file.
      </p>

      {error && (
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>
      )}

      {settings && (
        <div className="mt-6 divide-y divide-slate-100 rounded-xl border border-slate-200 bg-white shadow-sm">
          {Object.entries(LABELS).map(([key, label]) => (
            <div key={key} className="flex items-center justify-between px-5 py-3 text-sm">
              <span className="text-slate-500">{label}</span>
              <span className="font-medium text-slate-800">{String(settings[key])}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
