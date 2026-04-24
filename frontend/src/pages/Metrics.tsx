import { useEffect, useState } from "react";
import { getMetrics, getROI } from "../api/client";

interface MetricsData {
  top1_accuracy: number | null;
  top3_accuracy: number | null;
  mttd_ms: number | null;
  sample_size: number;
  note?: string;
}

interface ROIData {
  failures_processed: number;
  flaky_caught: number;
  minutes_saved: number;
  hours_saved: number;
  money_saved_usd: number;
  llm_cost_usd: number;
  net_savings_usd: number;
  roi_multiplier: number;
  assumptions: {
    minutes_saved_per_failure: number;
    dev_hourly_usd: number;
    llm_cost_per_rca_usd: number;
  };
  note?: string;
}

export default function Metrics() {
  const [m, setM] = useState<MetricsData | null>(null);
  const [roi, setROI] = useState<ROIData | null>(null);

  useEffect(() => {
    const fetchAll = () => {
      getMetrics().then((d) => setM(d as unknown as MetricsData));
      getROI().then((d) => setROI(d as unknown as ROIData));
    };
    fetchAll();
    const i = setInterval(fetchAll, 5000);
    return () => clearInterval(i);
  }, []);

  const pct = (v: number | null) =>
    v == null ? "—" : `${(v * 100).toFixed(0)}%`;
  const ms = (v: number | null) =>
    v == null ? "—" : `${(v / 1000).toFixed(1)} s`;
  const fmtUSD = (v: number) =>
    "$" + v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const fmtInt = (v: number) =>
    v.toLocaleString("en-US");

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {/* ── ROI SECTION ──────────────────────────────────── */}
      <h1 className="text-3xl font-bold mb-1">💰 Return on Investment</h1>
      <p className="text-neutral-600 mb-6">
        Real-time savings from automated root-cause analysis.
      </p>

      {roi ? (
        <div className="mb-10">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <ROICard label="Failures Processed" value={fmtInt(roi.failures_processed)} color="text-neutral-900" />
            <ROICard label="Developer Hours Saved" value={`${roi.hours_saved} hrs`} color="text-blue-600" />
            <ROICard label="Money Saved" value={fmtUSD(roi.money_saved_usd)} color="text-green-600" />
            <ROICard label="LLM Cost" value={fmtUSD(roi.llm_cost_usd)} color="text-neutral-500" />
          </div>

          <div className="p-6 bg-white border rounded-lg text-center">
            <div className="text-5xl md:text-6xl font-extrabold text-green-600 tabular-nums">
              {fmtUSD(roi.net_savings_usd)}
            </div>
            <div className="text-lg text-neutral-700 mt-1">Net Savings</div>
            <div className="text-3xl font-bold text-purple-600 mt-3 tabular-nums">
              {roi.roi_multiplier > 0 ? `${fmtInt(Math.round(roi.roi_multiplier))}×` : "—"}
            </div>
            <div className="text-sm text-neutral-600 mt-1">ROI Multiplier</div>
          </div>

          <p className="text-xs text-neutral-500 italic mt-4">
            Based on: {roi.assumptions.minutes_saved_per_failure / 60}hrs manual debugging per failure, ${roi.assumptions.dev_hourly_usd}/hr dev cost, ${roi.assumptions.llm_cost_per_rca_usd} per Claude API call.
          </p>
          <p className="text-xs text-neutral-500 mt-1">
            ⚡ Flaky failures caught: <span className="font-semibold">{roi.flaky_caught}</span> (each saves ~30 extra mins of wasted investigation)
          </p>
          {roi.note && (
            <p className="text-sm text-neutral-500 italic mt-2">{roi.note}</p>
          )}
        </div>
      ) : (
        <div className="mb-10 p-8 text-center text-neutral-500">Loading ROI data…</div>
      )}

      {/* ── EXISTING ACCURACY METRICS ────────────────────── */}
      <h2 className="text-2xl font-bold mb-1">Evaluation Metrics</h2>
      <p className="text-neutral-600 mb-6">
        Performance on labeled real GitHub Actions failures.
      </p>

      {m ? (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard
              label="Top-1 Accuracy"
              value={pct(m.top1_accuracy)}
              target="≥70%"
            />
            <MetricCard
              label="Top-3 Accuracy"
              value={pct(m.top3_accuracy)}
              target="≥90%"
            />
            <MetricCard
              label="Mean Time to Diagnosis"
              value={ms(m.mttd_ms)}
              target="<15s"
            />
            <MetricCard
              label="Sample Size"
              value={String(m.sample_size)}
              target="≥3"
            />
          </div>

          {m.note && (
            <p className="mt-6 text-sm text-neutral-500 italic">{m.note}</p>
          )}
        </>
      ) : (
        <div className="p-8 text-center text-neutral-500">Loading metrics…</div>
      )}
    </div>
  );
}

function ROICard({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div className="p-6 bg-white border rounded-lg">
      <div className="text-sm text-neutral-600">{label}</div>
      <div className={`text-3xl font-bold mt-2 tabular-nums ${color}`}>{value}</div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  target,
}: {
  label: string;
  value: string;
  target: string;
}) {
  return (
    <div className="p-6 bg-white border rounded-lg">
      <div className="text-sm text-neutral-600">{label}</div>
      <div className="text-4xl font-bold mt-2 tabular-nums">{value}</div>
      <div className="text-xs text-neutral-500 mt-1">Target: {target}</div>
    </div>
  );
}
