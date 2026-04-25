import React, { useEffect, useState } from "react";
import { getMetrics, getROI } from "../api/client";
import type { MetricsData, ROIData } from "../api/client";
import { LiveIndicator } from "../components/LiveIndicator";

export const Metrics: React.FC = () => {
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [roi, setRoi] = useState<ROIData | null>(null);

  const loadAll = async () => {
    try {
      const [mData, rData] = await Promise.all([getMetrics(), getROI()]);
      setMetrics(mData);
      setRoi(rData);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadAll();
    const interval = setInterval(loadAll, 5000);
    return () => clearInterval(interval);
  }, []);

  if (!metrics || !roi) {
    return (
      <div className="p-8 space-y-8">
        <div className="h-48 bg-slate-900 rounded-xl animate-pulse"></div>
        <div className="h-48 bg-slate-900 rounded-xl animate-pulse"></div>
      </div>
    );
  }

  // Fallback calculations if backend ROI is unpopulated
  const proc = roi.failures_processed || metrics.sample_size || 0;
  let savedHr = roi.hours_saved;
  let savedMoney = roi.money_saved_usd;
  let netSavings = roi.net_savings_usd;
  let mult = roi.roi_multiplier;
  let llmCost = roi.llm_cost_usd;
  const flakyCount = roi.flaky_caught || 0;

  if (savedHr === 0 && proc > 0) {
    // 2 hours per failure
    savedHr = proc * 2;
    savedMoney = savedHr * 100; // $100/hr
    llmCost = proc * 0.04;
    netSavings = savedMoney - llmCost;
    mult = savedMoney / (llmCost || 1);
  }

  const formatCurrency = (n: number) => {
    return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);
  };

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-12 pb-20">
      
      {/* ROI SECTION */}
      <section>
        <div className="flex items-center gap-4 mb-8">
          <h1 className="text-3xl font-bold text-white">💰 Return on Investment</h1>
          <LiveIndicator />
        </div>

        {/* HERO STAT */}
        <div className="bg-slate-900 ring-1 ring-white/5 rounded-3xl p-10 text-center mb-6 relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-b from-emerald-900/20 to-transparent pointer-events-none"></div>
          <div className="relative z-10">
            <h2 className="text-slate-400 text-sm font-bold uppercase tracking-widest mb-2">Net Savings</h2>
            <div className="text-6xl md:text-8xl font-black text-emerald-400 tracking-tight drop-shadow-md">
              {formatCurrency(netSavings).replace(".00", "")}
            </div>
            <div className="mt-4 inline-block bg-purple-900/30 text-purple-400 border border-purple-500/30 px-4 py-1.5 rounded-full text-lg font-bold tracking-wide">
              ROI Multiplier: {mult.toFixed(1)}x
            </div>
          </div>
        </div>

        {/* 4-CARD GRID */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
          <div className="bg-slate-900 rounded-xl p-6 ring-1 ring-white/5">
            <div className="text-4xl font-bold text-white mb-1">{proc}</div>
            <div className="text-slate-400 text-sm">pipeline failures analyzed</div>
          </div>
          <div className="bg-slate-900 rounded-xl p-6 ring-1 ring-white/5">
            <div className="text-4xl font-bold text-blue-400 mb-1">{savedHr}</div>
            <div className="text-slate-400 text-sm">hours saved of engineering time</div>
          </div>
          <div className="bg-slate-900 rounded-xl p-6 ring-1 ring-white/5">
            <div className="text-4xl font-bold text-emerald-400 mb-1">{formatCurrency(savedMoney).replace(".00", "")}</div>
            <div className="text-slate-400 text-sm">dollar value recovered</div>
          </div>
          <div className="bg-slate-900 rounded-xl p-6 ring-1 ring-white/5">
            <div className="text-4xl font-bold text-violet-400 mb-1">⚡ {flakyCount}</div>
            <div className="text-slate-400 text-sm">false alarms intercepted</div>
          </div>
        </div>

        <div className="flex justify-between items-center text-xs text-slate-500 px-2 mt-4">
          <div>Total AI Cost: {formatCurrency(llmCost)}</div>
          <div className="italic">
            Based on {roi.assumptions.minutes_saved_per_failure}m per RCA, ${roi.assumptions.dev_hourly_usd}/hr engineering cost, & ${roi.assumptions.llm_cost_per_rca_usd}/prompt.
          </div>
        </div>
      </section>

      <hr className="border-slate-800" />

      {/* ACCURACY SECTION */}
      <section>
        <div className="flex items-center gap-3 mb-6">
          <h2 className="text-2xl font-bold text-white">📊 Evaluation Accuracy</h2>
          <span className="bg-slate-800 text-slate-400 text-xs px-2 py-1 rounded border border-slate-700">
            n = {metrics.sample_size}
          </span>
        </div>

        {metrics.sample_size === 0 ? (
          <div className="bg-slate-900 rounded-xl p-8 border border-slate-800 text-center">
            <h3 className="text-lg font-medium text-white mb-2">Label failures to activate accuracy metrics</h3>
            <p className="text-slate-400 mb-6 max-w-lg mx-auto">
              Supply ground truth labels via the API to automatically evaluate AI diagnostic performance.
            </p>
            <code className="bg-slate-950 p-3 rounded text-sm text-indigo-300 border border-slate-800 inline-block font-mono">
              curl -X POST http://localhost:8000/eval/label -H "Content-Type: application/json" -d '&#123;"failure_id": "...", "correct_class": "dependency"&#125;'
            </code>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-slate-900 rounded-xl p-6 ring-1 ring-white/5">
              <h3 className="text-slate-400 text-sm mb-2">Top-1 Accuracy</h3>
              <div className={`text-4xl font-bold ${(metrics.top1_accuracy ?? 0) >= 0.7 ? "text-emerald-400" : "text-rose-400"}`}>
                {metrics.top1_accuracy ? (metrics.top1_accuracy * 100).toFixed(1) : "—"}%
              </div>
              <div className="text-xs text-slate-500 mt-2">Target ≥ 70.0%</div>
            </div>
            <div className="bg-slate-900 rounded-xl p-6 ring-1 ring-white/5">
              <h3 className="text-slate-400 text-sm mb-2">Top-3 Accuracy</h3>
              <div className={`text-4xl font-bold ${(metrics.top3_accuracy ?? 0) >= 0.9 ? "text-emerald-400" : "text-amber-400"}`}>
                {metrics.top3_accuracy ? (metrics.top3_accuracy * 100).toFixed(1) : "—"}%
              </div>
              <div className="text-xs text-slate-500 mt-2">Target ≥ 90.0%</div>
            </div>
            <div className="bg-slate-900 rounded-xl p-6 ring-1 ring-white/5">
              <h3 className="text-slate-400 text-sm mb-2">Mean Diagnosis Time</h3>
              <div className={`text-4xl font-bold ${metrics.mttd_ms && metrics.mttd_ms < 15000 ? "text-emerald-400" : "text-amber-400"}`}>
                {metrics.mttd_ms ? (metrics.mttd_ms / 1000).toFixed(1) : "—"}s
              </div>
              <div className="text-xs text-slate-500 mt-2">Target &lt; 15.0s</div>
            </div>
          </div>
        )}
      </section>

    </div>
  );
};
