const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export interface FailureSummary {
  id: string;
  repo: string;
  workflow: string;
  job: string;
  conclusion: string;
  triggered_at: string;
  has_rca: boolean;
  summary: string | null;
}

export async function listFailures(): Promise<FailureSummary[]> {
  const r = await fetch(`${BASE}/failures?limit=50`);
  if (!r.ok) throw new Error("failed to list failures");
  return r.json();
}

export async function getFailure(id: string): Promise<Record<string, unknown>> {
  const r = await fetch(`${BASE}/failures/${id}`);
  if (!r.ok) throw new Error("failed to get failure");
  return r.json();
}

export async function getMetrics(): Promise<Record<string, unknown>> {
  const r = await fetch(`${BASE}/metrics`);
  if (!r.ok) throw new Error("failed to get metrics");
  return r.json();
}
