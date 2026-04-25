import React, { useEffect, useState } from "react";
import { listFailures, seedFailures } from "../api/client";
import type { FailureSummary } from "../api/client";
import { useWebSocket } from "../hooks/useWebSocket";
import { StatusBadge } from "../components/StatusBadge";
import { LiveIndicator } from "../components/LiveIndicator";
import { navigate } from "../App";

export const Feed: React.FC = () => {
  const [failures, setFailures] = useState<FailureSummary[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      const data = await listFailures();
      setFailures(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 3000);
    return () => clearInterval(interval);
  }, []);

  useWebSocket((msg) => {
    if (msg.type === "new_failure" || msg.type === "rca_ready") {
      loadData();
    }
  });

  const handleSeed = async () => {
    await seedFailures();
    loadData();
  };

  const timeAgo = (isoString: string) => {
    const min = Math.floor((Date.now() - new Date(isoString).getTime()) / 60000);
    if (min < 1) return "just now";
    if (min < 60) return `${min}m ago`;
    const hr = Math.floor(min / 60);
    if (hr < 24) return `${hr}h ago`;
    return `${Math.floor(hr / 24)}d ago`;
  };

  return (
    <div className="p-8">
      {/* HEADER SECTION */}
      <div className="flex justify-between items-end mb-8 border-b border-slate-800 pb-6">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Pipeline Failures</h1>
          <p className="text-slate-400">Real-time RCA feed — AI diagnoses failures in ~15 seconds</p>
        </div>
        <div className="flex items-center gap-4">
          <LiveIndicator />
          <span className="bg-slate-800 text-slate-300 text-xs font-bold px-3 py-1 rounded-full">
            {failures.length} issues
          </span>
          <button 
            onClick={handleSeed}
            className="bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium py-2 px-4 rounded-lg transition-colors"
          >
            Seed Demo Data
          </button>
        </div>
      </div>

      {loading && failures.length === 0 ? (
        <div className="space-y-4">
          {[1,2,3].map(i => (
            <div key={i} className="h-28 bg-slate-900 rounded-xl animate-pulse ring-1 ring-white/5"></div>
          ))}
        </div>
      ) : failures.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-16 bg-slate-900/50 rounded-2xl ring-1 ring-white/5 mt-10">
          <div className="text-6xl text-slate-700 mb-6 font-mono font-light">⌇</div>
          <h2 className="text-xl font-bold text-white mb-2">Waiting for pipeline failures...</h2>
          <p className="text-slate-400 text-center max-w-md mb-8">
            Your backend is connected. Trigger a failure in your repository to see AI-powered diagnosis in real-time.
          </p>
          <div className="flex gap-4">
            <button 
              onClick={handleSeed}
              className="bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium py-2 px-6 rounded-lg transition-colors"
            >
              Seed Demo Data
            </button>
            <a 
              href="https://github.com" 
              target="_blank" 
              rel="noreferrer"
              className="bg-slate-800 hover:bg-slate-700 text-white text-sm font-medium py-2 px-6 rounded-lg transition-colors"
            >
              View GitHub Actions →
            </a>
          </div>
          <p className="text-xs text-slate-600 mt-6 mt-8 font-mono">
            VITE_API_BASE: {import.meta.env.VITE_API_BASE ?? "http://localhost:8000"}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {failures.map(f => (
            <div 
              key={f.id}
              onClick={() => navigate(`/failure/${f.id}`)}
              className="bg-slate-900 ring-1 ring-white/5 rounded-xl p-5 hover:ring-indigo-500/50 hover:bg-slate-800/80 cursor-pointer transition-all duration-200 flex flex-col md:flex-row justify-between gap-4"
            >
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-1">
                  <h3 className="font-semibold text-white truncate max-w-sm md:max-w-md">{f.repo}</h3>
                  <span className="text-slate-500 text-sm">{timeAgo(f.triggered_at)}</span>
                </div>
                <div className="text-slate-400 text-sm font-medium mb-3">
                  {f.workflow} · <span className="font-mono text-xs">{f.job}</span>
                </div>
                
                {f.has_rca && f.summary ? (
                  <div>
                    <p className="text-slate-300 text-sm line-clamp-2">{f.summary}</p>
                    {f.is_flaky && (
                      <p className="text-violet-400 text-xs mt-2 font-medium">⚡ Flaky — retry first</p>
                    )}
                  </div>
                ) : (
                  <div className="flex items-center gap-2 text-indigo-400 text-sm mt-2">
                    <span className="relative flex h-2 w-2 mr-1">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
                    </span>
                    Diagnosing root cause...
                  </div>
                )}
              </div>
              
              <div className="flex items-start gap-2 shrink-0">
                <StatusBadge status={f.conclusion} />
                {f.is_flaky && <StatusBadge status="flaky" />}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
