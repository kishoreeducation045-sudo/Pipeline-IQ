# app/llm/prompts.py

RCA_SYSTEM_PROMPT = """You are PipelineIQ, a senior DevOps engineer specialized in diagnosing CI/CD pipeline failures. You analyze logs, code diffs, test results, and candidate hypotheses to produce accurate root-cause analyses.

YOUR RESPONSIBILITIES:
1. Identify the most likely root cause from the candidates provided (you may also propose a better one if warranted).
2. Rank up to 3 hypotheses by confidence.
3. For each hypothesis, cite specific evidence from the logs, diff, or tests — quote exact snippets when possible.
4. Recommend ONE concrete remediation action with rationale and (if applicable) exact commands.

OUTPUT RULES:
- Respond ONLY with valid JSON matching the schema below. No prose before or after. No code fences.
- Use failure_class from this set ONLY:
  dependency_conflict, flaky_test, config_drift, resource_exhaustion, code_regression, infrastructure_error, unknown
- Confidence is a float 0.0–1.0. Do not inflate confidence; be calibrated.
- Evidence must include exact snippets copied from the provided input. Invent nothing.
- Remediation risk_level is one of: low, medium, high.
- If you cannot determine cause, return a single "unknown" hypothesis with low confidence and explain what additional data would help.

OUTPUT SCHEMA (all fields required unless marked optional):
{
  "failure_id": "string (copy from input)",
  "generated_at": "ISO 8601 string",
  "hypotheses": [
    {
      "rank": 1,
      "title": "short headline",
      "description": "2-3 sentence explanation",
      "failure_class": "one of the enum values",
      "confidence": 0.0-1.0,
      "evidence": [
        {
          "source": "log|diff|test|commit",
          "location": "e.g. logs:Install dependencies or diff:requirements.txt",
          "snippet": "exact text from input",
          "relevance_score": 0.0-1.0
        }
      ]
    }
  ],
  "recommended_remediation": {
    "action": "short action name",
    "rationale": "why this fixes it",
    "commands": ["optional shell commands"],
    "risk_level": "low|medium|high"
  },
  "summary": "single-sentence plain-English summary of the failure",
  "latency_ms": 0,
  "similar_past_failures": []
}
"""

from app.models.failure import FailureContext
from app.detection.rules import Candidate

def build_user_prompt(
    ctx: FailureContext,
    candidates: list[Candidate],
    similar_failures: list[dict],
    flaky_result: dict | None = None,
) -> str:
    # Select most relevant log lines (errors + surrounding context)
    error_indices = [i for i, l in enumerate(ctx.logs) if l.level == "error"]
    relevant_log_indices = set()
    for idx in error_indices:
        for off in range(-3, 4):  # 3 lines before and after each error
            if 0 <= idx + off < len(ctx.logs):
                relevant_log_indices.add(idx + off)
    relevant_logs = [ctx.logs[i] for i in sorted(relevant_log_indices)][:80]
    log_text = "\n".join(f"[{l.step}][{l.level}] {l.message}" for l in relevant_logs)

    # Diff summary — top 3 files, truncate long hunks
    diff_parts = []
    for h in ctx.diff_hunks[:3]:
        diff_parts.append(f"--- FILE: {h.file_path} ({h.change_type}) ---")
        for old in h.old_lines[:10]:
            diff_parts.append(f"- {old}")
        for new in h.new_lines[:10]:
            diff_parts.append(f"+ {new}")
    diff_text = "\n".join(diff_parts) if diff_parts else "(no diff)"

    # Candidate summary
    cand_parts = []
    for i, c in enumerate(candidates, 1):
        cand_parts.append(
            f"[{i}] class={c.failure_class} prior={c.confidence_prior:.2f} rule={c.rule_id}\n"
            f"    evidence_loc={c.evidence_locations}\n"
            f"    snippet={c.snippet[:200]}"
        )
    cand_text = "\n".join(cand_parts) if cand_parts else "(no candidates from rule layer)"

    # Similar past failures
    sim_parts = []
    for s in similar_failures:
        sim_parts.append(
            f"- past_failure_id={s['id']} class={s['metadata'].get('failure_class','?')}\n"
            f"  summary: {s['document'][:300]}"
        )
    sim_text = "\n".join(sim_parts) if sim_parts else "(no similar past failures found)"

    # Flaky signals section
    flaky_section = ""
    if flaky_result and flaky_result.get("is_flaky"):
        flaky_section = f"""
FLAKY SIGNALS DETECTED (rule-based heuristic):
  Category: {flaky_result.get('flaky_category', 'unknown')}
  Score: {flaky_result.get('flaky_score', 0)}
  Matched: {flaky_result.get('matched_signals', [])}

  Note: These patterns often indicate transient/infrastructure failures.
  Weigh this as supporting evidence but use your own judgment.
"""

    return f"""FAILURE ID: {ctx.id}
REPO: {ctx.repo_full_name}
WORKFLOW: {ctx.workflow_name}
JOB: {ctx.job_name}
CONCLUSION: {ctx.conclusion}
DURATION: {ctx.duration_seconds}s

HEAD COMMIT:
  sha: {ctx.head_commit.sha}
  author: {ctx.head_commit.author}
  message: {ctx.head_commit.message}
  files_changed: {ctx.head_commit.files_changed}

RELEVANT LOG SNIPPETS (error-adjacent, ~{len(relevant_logs)} lines):
{log_text}

CODE DIFF (top 3 files, truncated):
{diff_text}

CANDIDATES FROM RULE-BASED DETECTOR (ranked by prior confidence):
{cand_text}

SIMILAR PAST FAILURES (from knowledge base):
{sim_text}
{flaky_section}
Produce the RCA JSON per the schema in your system prompt. Set failure_id="{ctx.id}".
"""
