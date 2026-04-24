import { useEffect, useState } from "react";
import { getFailure } from "../api/client";

interface FailureData {
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

interface Evidence {
  source: string;
  location: string;
  snippet: string;
}

interface Hypothesis {
  rank: number;
  title: string;
  confidence: number;
  description: string;
  failure_class: string;
  evidence: Evidence[];
}

interface Remediation {
  action: string;
  rationale: string;
  commands: string[];
  risk_level: string;
}

interface RCAData {
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
}

interface FailureDetailResponse {
  failure: FailureData;
  rca: RCAData | null;
}

export default function FailureDetail({ id }: { id: string }) {
  const [data, setData] = useState<FailureDetailResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getFailure(id)
      .then((d) => setData(d as FailureDetailResponse))
      .catch((e) => setError(String(e)));
  }, [id]);

  if (error) return <div className="p-8 text-red-600">Error: {error}</div>;
  if (!data) return <div className="p-8">Loading…</div>;

  const { failure, rca } = data;
  return (
    <div className="p-8 max-w-4xl mx-auto">
      <a href="/" className="text-sm text-blue-600 hover:underline">
        ← back to feed
      </a>
      <h1 className="text-2xl font-bold mt-2">{failure.repo_full_name}</h1>
      <div className="text-neutral-600">
        {failure.workflow_name} · {failure.job_name}
      </div>
      <a
        href={failure.run_url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-xs text-blue-600 hover:underline"
      >
        View run on GitHub →
      </a>

      {rca ? (
        <div className="mt-6 space-y-6">
          <section className="p-4 bg-white border rounded-lg">
            <h2 className="text-lg font-semibold">Summary</h2>
            <p className="mt-2">{rca.summary}</p>
            <div className="text-xs text-neutral-500 mt-2">
              Diagnosed in {rca.latency_ms} ms
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold mb-3">Ranked Hypotheses</h2>
            <div className="space-y-3">
              {rca.hypotheses_json.map((h: Hypothesis, i: number) => (
                <div key={i} className="p-4 bg-white border rounded-lg">
                  <div className="flex justify-between items-start">
                    <div className="font-medium">
                      #{h.rank} · {h.title}
                    </div>
                    <div className="text-sm font-semibold text-blue-600">
                      {(h.confidence * 100).toFixed(0)}%
                    </div>
                  </div>
                  <p className="text-sm mt-1">{h.description}</p>
                  <div className="text-xs text-neutral-500 mt-1">
                    class: <code>{h.failure_class}</code>
                  </div>
                  <div className="mt-3 space-y-1">
                    {h.evidence.map((e: Evidence, j: number) => (
                      <div
                        key={j}
                        className="text-xs bg-neutral-50 p-2 rounded border"
                      >
                        <div className="text-neutral-600">
                          <b>{e.source}</b>:{e.location}
                        </div>
                        <pre className="mt-1 whitespace-pre-wrap font-mono break-words">
                          {e.snippet}
                        </pre>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="p-4 bg-green-50 border border-green-200 rounded-lg">
            <h2 className="text-lg font-semibold">Recommended Remediation</h2>
            <div className="mt-2 font-medium">
              {rca.recommended_remediation.action}
            </div>
            <p className="text-sm mt-1">
              {rca.recommended_remediation.rationale}
            </p>
            {rca.recommended_remediation.commands?.length > 0 && (
              <pre className="mt-2 p-3 bg-neutral-900 text-neutral-100 text-xs rounded overflow-x-auto">
                {rca.recommended_remediation.commands.join("\n")}
              </pre>
            )}
            <div className="text-xs mt-2">
              Risk: <b>{rca.recommended_remediation.risk_level}</b>
            </div>
          </section>

          {rca.similar_past_failures?.length > 0 && (
            <section className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <h2 className="text-lg font-semibold">Similar Past Failures</h2>
              <p className="text-xs text-neutral-600 mb-2">
                Retrieved from our knowledge base — PipelineIQ learns over time.
              </p>
              <ul className="text-sm space-y-1">
                {rca.similar_past_failures.map((pastId: string) => (
                  <li key={pastId}>
                    <a
                      href={`/failure/${pastId}`}
                      className="text-blue-600 hover:underline"
                    >
                      {pastId}
                    </a>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      ) : (
        <div className="mt-6 p-4 bg-amber-50 border border-amber-200 rounded">
          Diagnosing… RCA will appear here in ~15 seconds.
        </div>
      )}
    </div>
  );
}
