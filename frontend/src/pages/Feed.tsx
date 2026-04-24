import { useEffect, useState } from "react";
import { listFailures } from "../api/client";
import type { FailureSummary } from "../api/client";
import { useWebSocket } from "../hooks/useWebSocket";

export default function Feed() {
  const [items, setItems] = useState<FailureSummary[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    try {
      setItems(await listFailures());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const load = async () => {
      try {
        setItems(await listFailures());
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    load();
    const interval = setInterval(load, 3000);
    return () => clearInterval(interval);
  }, []);

  useWebSocket((msg) => {
    if (msg.type === "rca_ready") refresh();
  });

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <h1 className="text-3xl font-bold mb-1">Pipeline Failures</h1>
      <p className="text-neutral-600 mb-6">
        Live feed of CI/CD failures with AI-diagnosed root causes.
      </p>

      {loading && <p className="text-neutral-500">Loading…</p>}
      {!loading && items.length === 0 && (
        <div className="p-12 text-center bg-white border-2 border-dashed rounded-lg">
          <p className="text-neutral-500">
            No failures yet. Push a bad commit to your test repo.
          </p>
        </div>
      )}

      <div className="space-y-3">
        {items.map((f) => (
          <a
            key={f.id}
            href={`/failure/${f.id}`}
            className="block p-4 bg-white border rounded-lg shadow-sm hover:shadow-md hover:border-neutral-300 transition"
          >
            <div className="flex justify-between items-start gap-4">
              <div className="flex-1 min-w-0">
                <div className="font-medium truncate">{f.repo}</div>
                <div className="text-sm text-neutral-600">
                  {f.workflow} · {f.job}
                </div>
                {f.summary && (
                  <p className="mt-2 text-sm text-neutral-800 line-clamp-2">
                    {f.summary}
                  </p>
                )}
              </div>
              <div className="text-xs text-right shrink-0">
                <div
                  className={`inline-block px-2 py-1 rounded font-medium ${
                    f.conclusion === "failure"
                      ? "bg-red-100 text-red-700"
                      : "bg-amber-100 text-amber-700"
                  }`}
                >
                  {f.conclusion}
                </div>
                <div className="text-neutral-500 mt-1">
                  {new Date(f.triggered_at).toLocaleTimeString()}
                </div>
              </div>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
