import { useEffect, useState } from "react";
import { getMetrics } from "../api/client";

interface MetricsData {
  top1_accuracy: number | null;
  top3_accuracy: number | null;
  mttd_ms: number | null;
  sample_size: number;
  note?: string;
}

export default function Metrics() {
  const [m, setM] = useState<MetricsData | null>(null);

  useEffect(() => {
    getMetrics().then((d) => setM(d as MetricsData));
    const i = setInterval(() => getMetrics().then((d) => setM(d as MetricsData)), 5000);
    return () => clearInterval(i);
  }, []);

  if (!m) return <div className="p-8">Loading metrics…</div>;

  const pct = (v: number | null) =>
    v == null ? "—" : `${(v * 100).toFixed(0)}%`;
  const ms = (v: number | null) =>
    v == null ? "—" : `${(v / 1000).toFixed(1)} s`;

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <h1 className="text-3xl font-bold mb-1">Evaluation Metrics</h1>
      <p className="text-neutral-600 mb-6">
        Performance on labeled real GitHub Actions failures.
      </p>

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
