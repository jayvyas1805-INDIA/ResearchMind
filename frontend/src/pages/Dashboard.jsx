export default function Dashboard() {
  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <h1 className="text-2xl font-semibold text-slate-800">Dashboard</h1>
      <p className="mt-2 text-slate-500">
        Your uploaded papers and processing status will appear here.
      </p>

      <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-sm text-slate-500">Total Papers</p>
          <p className="mt-1 text-2xl font-semibold text-slate-800">0</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-sm text-slate-500">Processed</p>
          <p className="mt-1 text-2xl font-semibold text-slate-800">0</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-sm text-slate-500">Pending</p>
          <p className="mt-1 text-2xl font-semibold text-slate-800">0</p>
        </div>
      </div>

      <div className="mt-10 rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center text-slate-400">
        No papers uploaded yet — this list will populate starting Phase 2 and
        beyond.
      </div>
    </div>
  );
}
