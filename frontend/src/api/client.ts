const BASE = (import.meta.env.VITE_API_BASE as string) ?? "http://localhost:8000";

export interface FailureSummary {
  id: string;
  repo: string;
  workflow: string;
  job: string;
  conclusion: string;
  triggered_at: string;
  has_rca: boolean;
  summary: string | null;
  is_flaky?: boolean;
}

export interface Evidence {
  source: string;
  location: string;
  snippet: string;
  relevance_score?: number;
}

export interface Hypothesis {
  rank: number;
  title: string;
  description: string;
  failure_class: string;
  confidence: number;
  evidence: Evidence[];
}

export interface Remediation {
  action: string;
  rationale: string;
  commands: string[];
  risk_level: string;
}

export interface FlakyAssessment {
  is_flaky: boolean;
  flaky_score: number;
  flaky_category: string | null;
  matched_signals: { keyword: string; category: string; log_line: string }[];
  recommended_action: string;
}

export interface RCAData {
  id: string;
  failure_id: string;
  generated_at: string;
  summary: string;
  hypotheses_json: Hypothesis[];
  recommended_remediation: Remediation;
  similar_past_failures: string[];
  latency_ms: number;
  top1_class: string;
  ground_truth_class: string | null;
  flaky_assessment?: FlakyAssessment | null;
}

export interface FailureDetail {
  id: string;
  provider: string;
  repo_full_name: string;
  workflow_name: string;
  job_name: string;
  run_id: string;
  run_url: string;
  conclusion: string;
  triggered_at: string;
  completed_at: string;
  duration_seconds: number;
}

export interface MetricsData {
  top1_accuracy: number | null;
  top3_accuracy: number | null;
  mttd_ms: number | null;
  sample_size: number;
  note?: string;
}

export interface ROIData {
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

export async function listFailures(): Promise<FailureSummary[]> {
  const r = await fetch(`${BASE}/failures?limit=50`);
  if (!r.ok) throw new Error(`Backend error: ${r.status}`);
  return r.json();
}

export async function getFailure(id: string): Promise<{ failure: FailureDetail; rca: RCAData | null }> {
  const r = await fetch(`${BASE}/failures/${id}`);
  if (!r.ok) throw new Error(`Backend error: ${r.status}`);
  return r.json();
}

export async function getMetrics(): Promise<MetricsData> {
  const r = await fetch(`${BASE}/metrics`);
  if (!r.ok) throw new Error(`Backend error: ${r.status}`);
  return r.json();
}

export async function getROI(): Promise<ROIData> {
  const fallback: ROIData = { failures_processed: 0, flaky_caught: 0, minutes_saved: 0, hours_saved: 0, money_saved_usd: 0, llm_cost_usd: 0, net_savings_usd: 0, roi_multiplier: 0, assumptions: { minutes_saved_per_failure: 120, dev_hourly_usd: 100, llm_cost_per_rca_usd: 0.04 } };
  try {
    const r = await fetch(`${BASE}/metrics/roi`);
    if (!r.ok) return fallback;
    return r.json();
  } catch {
    return fallback;
  }
}

export async function seedFailures(): Promise<void> {
  await fetch(`${BASE}/eval/seed`, { method: "POST" });
}
