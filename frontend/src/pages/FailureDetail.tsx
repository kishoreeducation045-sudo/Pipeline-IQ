import React, { useEffect, useState } from "react";
import { getFailure } from "../api/client";
import type { FailureDetail as FailureDetailType, RCAData } from "../api/client";
import { StatusBadge } from "../components/StatusBadge";
import { ConfidenceBar } from "../components/ConfidenceBar";
import { navigate } from "../App";

export const FailureDetail: React.FC<{ id: string }> = ({ id }) => {
  const [data, setData] = useState<{ failure: FailureDetailType; rca: RCAData | null } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getFailure(id)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="p-8 space-y-6">
        <div className="h-4 w-24 bg-slate-800 rounded animate-pulse" />
        <div className="h-32 bg-slate-900 rounded-xl animate-pulse" />
        <div className="h-64 bg-slate-900 rounded-xl animate-pulse" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8">
        <button onClick={() => navigate("/")} className="text-indigo-400 hover:text-indigo-300 mb-6 text-sm">
          ← Back to Feed
        </button>
        <div className="bg-rose-950/50 border border-rose-900 rounded-xl p-6 text-rose-400">
          Error loading details: {error || "Not found"}
        </div>
      </div>
    );
  }

  const { failure, rca } = data;
  const isFlaky = rca?.flaky_assessment?.is_flaky === true;
  const isClaude = import.meta.env.VITE_API_BASE?.includes("gemini") ? false : true;

  return (
    <div className="p-8 max-w-4xl mx-auto pb-20">
      <button onClick={() => navigate("/")} className="text-indigo-400 hover:text-indigo-300 mb-6 text-sm font-medium">
        ← Back to Feed
      </button>

      {/* HEADER CARD */}
      <div className="bg-slate-900 ring-1 ring-white/5 rounded-xl p-6 mb-6">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h1 className="text-2xl font-bold text-white mb-1">{failure.repo_full_name}</h1>
            <p className="text-slate-400">
              {failure.workflow_name} · <span className="font-mono">{failure.job_name}</span>
            </p>
          </div>
          <StatusBadge status={failure.conclusion} size="md" />
        </div>
        <div className="flex flex-wrap gap-3 mt-6">
          <span className="bg-slate-800 text-slate-300 px-3 py-1 rounded-full text-xs font-medium border border-slate-700">
            {failure.provider}
          </span>
          <span className="bg-slate-800 text-slate-300 px-3 py-1 rounded-full text-xs font-medium border border-slate-700">
            ⏱ {failure.duration_seconds}s
          </span>
          <a
            href={failure.run_url}
            target="_blank"
            rel="noreferrer"
            className="bg-slate-800 hover:bg-slate-700 text-white px-3 py-1 rounded-full text-xs font-medium border border-slate-700 transition-colors"
          >
            View on GitHub →
          </a>
        </div>
      </div>

      {!rca ? (
        <div className="bg-slate-900/50 rounded-xl p-10 flex flex-col items-center justify-center text-center">
          <div className="relative flex h-8 w-8 mb-4">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-8 w-8 bg-indigo-500"></span>
          </div>
          <p className="text-slate-300 font-medium">AI is diagnosing this failure...</p>
          <p className="text-slate-500 text-sm mt-2">This usually takes around 15 seconds.</p>
        </div>
      ) : (
        <div className="space-y-6">
          
          {/* FLAKY BANNER */}
          {isFlaky ? (
            <div className="bg-amber-950/30 border border-amber-500/50 rounded-xl p-5 relative overflow-hidden">
              <div className="flex items-start gap-4">
                <span className="text-3xl">⚡</span>
                <div className="flex-1">
                  <h2 className="text-amber-300 font-bold text-lg mb-1">Likely Flaky Infrastructure Issue</h2>
                  <p className="text-amber-200/80 text-sm mb-3">{rca.flaky_assessment?.recommended_action}</p>
                  
                  <div className="flex items-center gap-3 mb-4">
                    <span className="bg-amber-900/50 text-amber-400 px-2.5 py-0.5 border border-amber-700/50 rounded-full text-xs font-bold uppercase tracking-wider">
                      {rca.flaky_assessment?.flaky_category || "Network"}
                    </span>
                    <span className="text-amber-500/80 text-xs font-mono">
                      Score: {(rca.flaky_assessment!.flaky_score * 100).toFixed(0)}%
                    </span>
                  </div>

                  <details className="group">
                    <summary className="cursor-pointer text-amber-500 hover:text-amber-400 text-sm font-medium mb-2 select-none">
                      Show matched signals ({rca.flaky_assessment?.matched_signals.length})
                    </summary>
                    <div className="space-y-2 mt-3">
                      {rca.flaky_assessment?.matched_signals.map((sig, i) => (
                        <div key={i} className="bg-slate-950/50 p-3 rounded-lg border border-amber-900/30">
                          <span className="text-amber-600 text-xs font-bold uppercase mr-2">{sig.keyword}</span>
                          <code className="text-xs text-amber-200/70 font-mono break-all">{sig.log_line}</code>
                        </div>
                      ))}
                    </div>
                  </details>
                </div>
                <button className="bg-transparent border border-amber-500 text-amber-500 hover:bg-amber-950/50 px-4 py-2 rounded-lg text-sm font-bold transition-colors">
                  Retry Build
                </button>
              </div>
            </div>
          ) : rca.flaky_assessment && (
            <div className="bg-emerald-950/30 border border-emerald-900 rounded-lg p-3 flex items-center gap-2">
              <span className="text-emerald-500">✅</span>
              <span className="text-emerald-400/80 text-sm">No flaky patterns detected — this is a real structural bug.</span>
            </div>
          )}

          {/* SUMMARY CARD */}
          <div className="bg-slate-900 ring-1 ring-white/5 rounded-xl p-6">
            <h2 className="text-slate-400 text-sm font-bold tracking-wider uppercase mb-3 flex items-center gap-2">
              <span>🤖</span> AI Summary
            </h2>
            <p className="text-slate-200 text-lg italic leading-relaxed">"{rca.summary}"</p>
            <div className="mt-4 flex justify-between items-end border-t border-slate-800 pt-4">
              <span className="text-slate-600 text-xs">
                Powered by {isClaude ? "Claude 3.5 Sonnet" : "Gemini 2.5 Flash"}
              </span>
              <span className="text-slate-600 text-xs font-mono">
                Diagnosed in {rca.latency_ms}ms
              </span>
            </div>
          </div>

          {/* ROOT CAUSE HYPOTHESES */}
          <div>
            <div className="flex items-center gap-3 mb-4 mt-8">
              <h2 className="text-xl font-bold text-white">Root Cause Hypotheses</h2>
              <span className="bg-indigo-600 outline outline-2 outline-slate-950 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold">
                {rca.hypotheses_json.length}
              </span>
            </div>
            
            <div className="space-y-4">
              {rca.hypotheses_json.map((h, i) => (
                <div key={i} className="bg-slate-900 ring-1 ring-white/5 rounded-xl p-5">
                  <div className="flex gap-4">
                    <div className="shrink-0 pt-0.5">
                      <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-white font-bold">
                        {h.rank}
                      </div>
                    </div>
                    <div className="flex-1">
                      <div className="flex justify-between items-start mb-2">
                        <h3 className="font-bold text-white text-lg">{h.title}</h3>
                        <span className="bg-slate-800 text-slate-300 border border-slate-700 px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-wider">
                          {h.failure_class}
                        </span>
                      </div>
                      
                      <div className="mb-4">
                        <ConfidenceBar value={h.confidence} label="Confidence Score" />
                      </div>
                      
                      <p className="text-slate-300 text-sm mb-4">{h.description}</p>
                      
                      {h.evidence && h.evidence.length > 0 && (
                        <details className="group">
                          <summary className="text-indigo-400 hover:text-indigo-300 text-xs font-bold uppercase tracking-wider cursor-pointer select-none">
                            Supporting Evidence ({h.evidence.length})
                          </summary>
                          <div className="space-y-3 mt-3">
                            {h.evidence.map((ev, ei) => (
                              <div key={ei} className="bg-slate-950 rounded-lg p-3 ring-1 ring-slate-800">
                                <div className="flex items-center gap-2 mb-2">
                                  <span className="text-[10px] font-bold uppercase bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded">
                                    {ev.source}
                                  </span>
                                  <span className="text-slate-500 text-xs font-mono">{ev.location}</span>
                                </div>
                                <code className="block text-emerald-300 text-xs font-mono break-words whitespace-pre-wrap">
                                  {ev.snippet}
                                </code>
                              </div>
                            ))}
                          </div>
                        </details>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* REMEDIATION CARD */}
          {rca.recommended_remediation && (
            <div className="bg-emerald-950/20 border border-emerald-900/50 rounded-xl p-6 mt-8">
              <div className="flex justify-between items-start mb-4">
                <h2 className="text-emerald-400 font-bold text-lg flex items-center gap-2">
                  <span>🔧</span> Recommended Fix
                </h2>
                <span className="bg-emerald-900/50 text-emerald-500 px-2 py-1 rounded text-xs font-bold border border-emerald-800/50">
                  Risk: {rca.recommended_remediation.risk_level}
                </span>
              </div>
              
              <div className="space-y-4">
                <div>
                  <h3 className="text-emerald-200 font-medium text-sm mb-1">Action</h3>
                  <p className="text-emerald-100/70 text-sm">{rca.recommended_remediation.action}</p>
                </div>
                
                <div>
                  <h3 className="text-emerald-200 font-medium text-sm mb-1">Rationale</h3>
                  <p className="text-slate-300 text-sm">{rca.recommended_remediation.rationale}</p>
                </div>

                {rca.recommended_remediation.commands && rca.recommended_remediation.commands.length > 0 && (
                  <div>
                    <h3 className="text-emerald-200 font-medium text-sm mb-2">Commands / Fix</h3>
                    <div className="bg-slate-950 p-4 rounded-lg font-mono text-sm text-emerald-400 ring-1 ring-emerald-900/30 overflow-x-auto">
                      {rca.recommended_remediation.commands.map((cmd, i) => (
                        <div key={i}>{cmd}</div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

        </div>
      )}
    </div>
  );
};
