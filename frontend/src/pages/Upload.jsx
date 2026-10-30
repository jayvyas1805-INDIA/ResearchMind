import { useCallback, useRef, useState } from "react";
import { uploadPaper } from "../services/api.js";
import StatusBadge from "../components/StatusBadge.jsx";

export default function Upload() {
  const [dragActive, setDragActive] = useState(false);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState("idle"); // idle | uploading | done | error
  const [errorMessage, setErrorMessage] = useState("");
  const [result, setResult] = useState(null);
  const inputRef = useRef(null);

  const handleFile = useCallback(async (file) => {
    if (!file) return;

    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      setStatus("error");
      setErrorMessage("Only PDF files are supported.");
      return;
    }

    setStatus("uploading");
    setErrorMessage("");
    setProgress(0);
    setResult(null);

    try {
      const data = await uploadPaper(file, (pct) => setProgress(pct));
      setResult(data);
      setStatus("done");
    } catch (err) {
      setStatus("error");
      const detail = err?.response?.data?.detail;
      setErrorMessage(detail || "Something went wrong while uploading. Please try again.");
    }
  }, []);

  const onDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files?.[0];
    handleFile(file);
  };

  const onInputChange = (e) => {
    const file = e.target.files?.[0];
    handleFile(file);
  };

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <h1 className="text-2xl font-semibold text-slate-800">Upload a Paper</h1>
      <p className="mt-2 text-slate-500">
        Upload a research paper (PDF) to extract its text and metadata.
      </p>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={`mt-8 flex h-56 cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed text-center transition-colors ${
          dragActive
            ? "border-brand-500 bg-brand-50"
            : "border-slate-300 bg-white hover:border-brand-400"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          className="hidden"
          onChange={onInputChange}
        />
        <p className="text-slate-500">
          Drag & drop a PDF here, or{" "}
          <span className="font-medium text-brand-600">click to browse</span>
        </p>
        <p className="mt-1 text-xs text-slate-400">PDF only, up to 25 MB</p>
      </div>

      {status === "uploading" && (
        <div className="mt-6">
          <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
            <div
              className="h-full rounded-full bg-brand-500 transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="mt-2 text-sm text-slate-500">Uploading & extracting… {progress}%</p>
        </div>
      )}

      {status === "error" && (
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {errorMessage}
        </div>
      )}

      {status === "done" && result && (
        <div className="mt-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-800">{result.filename}</h2>
            <StatusBadge status={result.status} />
          </div>
          <dl className="mt-4 grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
            <div>
              <dt className="text-slate-400">Paper ID</dt>
              <dd className="truncate text-slate-700">{result.paper_id}</dd>
            </div>
            <div>
              <dt className="text-slate-400">Pages</dt>
              <dd className="text-slate-700">{result.page_count}</dd>
            </div>
          </dl>
        </div>
      )}
    </div>
  );
}
