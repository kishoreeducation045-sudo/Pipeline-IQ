# PipelineIQ — AI/LLM Orchestration & Evaluation Design

**Document 4 of 4** · Claude integration, hybrid anomaly detection, prompt engineering, evaluation methodology

---

## 1. Claude Integration Overview

### 1.1 Model Choice: Claude Sonnet 4.5

Chosen for:
- Strong structured-output reliability (Pydantic validation rarely fails)
- Reasoning quality on symbolic/textual failure data
- Tool use capability (for future expansion)
- Cost/latency balance appropriate for 15-second RCA target

**Model string to use in code:** `claude-sonnet-4-5`

> Before committing code, verify the exact model identifier by running a quick test against the Anthropic API. Model aliases sometimes change; if `claude-sonnet-4-5` isn't accepted, use the latest Sonnet model string returned from your API console.

### 1.2 SDK Setup

```python
# app/llm/client.py
from anthropic import AsyncAnthropic
from app.config import settings

class ClaudeClient:
    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model

    async def generate(
        self,
        system: str,
        user: str,
        max_tokens: int = 2048,
        temperature: float = 0.2,
    ) -> str:
        """Basic text generation. Returns raw string response."""
        msg = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        # Response is a list of content blocks; we extract text blocks
        return "".join(
            block.text for block in msg.content if block.type == "text"
        )

claude = ClaudeClient()
```

### 1.3 Token Budget Management

| Budget Line Item | Tokens | Notes |
|---|---|---|
| System prompt (fixed) | ~800 | Role, instructions, schema |
| User prompt — context headers | ~400 | Repo, commit info, timing |
| User prompt — logs (last 100 error-adjacent lines) | ~3000 | Truncate aggressively |
| User prompt — diff hunks | ~1500 | Top 3 changed files |
| User prompt — candidates (top 5 from hybrid detector) | ~800 | Summarized |
| User prompt — similar past failures (3 summaries) | ~500 | From ChromaDB |
| Output — RCA JSON | ~1500 | 3 hypotheses + remediation + evidence |
| **Target total per RCA** | **~8500** | Cost ~$0.035–0.05 |

**Hackathon budget: 100 RCA calls × $0.05 = $5.** Well within $10 buffer.

### 1.4 Error Handling & Retry

```python
# app/llm/client.py (extended)
import asyncio
import json
from anthropic import APIError, RateLimitError

class ClaudeClient:
    # ... existing init ...

    async def generate_with_retry(
        self,
        system: str,
        user: str,
        max_tokens: int = 2048,
        max_attempts: int = 3,
    ) -> str:
        delay = 1.0
        last_err = None
        for attempt in range(max_attempts):
            try:
                return await self.generate(system, user, max_tokens)
            except RateLimitError as e:
                last_err = e
                await asyncio.sleep(delay)
                delay *= 2
            except APIError as e:
                last_err = e
                if attempt < max_attempts - 1:
                    await asyncio.sleep(delay)
                    delay *= 2
                else:
                    raise
        raise last_err  # type: ignore

    async def generate_json(
        self,
        system: str,
        user: str,
        schema_model,  # Pydantic model class
        max_tokens: int = 2048,
        max_attempts: int = 2,
    ):
        """Generate, parse JSON, validate against Pydantic model; retry once on malformed."""
        for attempt in range(max_attempts):
            raw = await self.generate_with_retry(system, user, max_tokens)
            # Strip optional ```json fences
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```", 2)[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
                cleaned = cleaned.rstrip("`").strip()
            try:
                data = json.loads(cleaned)
                return schema_model.model_validate(data)
            except (json.JSONDecodeError, ValueError) as e:
                if attempt == max_attempts - 1:
                    raise
                # Ask Claude to fix its own output
                user = (
                    f"Your previous response was not valid JSON matching the required schema. "
                    f"Error: {e}\n\n"
                    f"Original response:\n{raw}\n\n"
                    f"Please return ONLY the corrected JSON, no prose, no code fences."
                )
```

---

## 2. Hybrid Anomaly Detection Architecture

The goal is not to rely on any single technique. Each layer compensates for the weaknesses of the others.

```
┌──────────────────────────────────────────────────────────────────┐
│                    HYBRID DETECTION PYRAMID                      │
│                                                                  │
│                           ┌─────────────┐                        │
│                           │   Layer 3   │   ← Few, rich          │
│                           │   Claude    │     Reasoning          │
│                           │  Reasoning  │     + Synthesis        │
│                           └──────▲──────┘                        │
│                                  │ top 5 candidates              │
│                        ┌─────────┴─────────┐                     │
│                        │      Layer 2      │  ← Structural       │
│                        │  Graph Centrality │     Scoring         │
│                        │     (NetworkX)    │                     │
│                        └─────────▲─────────┘                     │
│                                  │ candidates with scores        │
│              ┌───────────────────┴───────────────────┐           │
│              │              Layer 1                  │  ← Cheap  │
│              │   Rule-Based Pattern Matchers         │    Wide   │
│              │  (regex / keyword / heuristics)       │    Pass   │
│              └───────────────────────────────────────┘           │
│                                  ▲                               │
│                                  │ raw logs + diff + graph       │
└──────────────────────────────────────────────────────────────────┘
```

### 2.1 Why This Is Stronger Than Any Single Layer

| Layer | Strength | Weakness |
|---|---|---|
| Rules | Fast, deterministic, high precision on known patterns | Recall limited to patterns we wrote |
| Graph centrality | Captures blast radius & structural importance | Knows nothing about *why* failures matter |
| Claude reasoning | Handles novel cases, synthesizes multi-signal evidence, generates natural language | Slow, costs money, hallucinates without grounding |

**Combined:** Rules provide *high-precision candidates*, graph adds *structural ranking*, Claude adds *reasoning + explanation*. We pass only top candidates to Claude — avoiding the "huge log dump to LLM" antipattern that wastes tokens and yields poor results.

### 2.2 Layer 1: Rule-Based Pattern Matchers

```python
# app/detection/rules.py
import re
from dataclasses import dataclass
from app.models.failure import FailureContext

@dataclass
class Candidate:
    failure_class: str
    confidence_prior: float       # Prior before graph/LLM
    evidence_locations: list[str] # e.g. ["logs:line 42", "diff:requirements.txt"]
    snippet: str                  # The actual matched text
    rule_id: str

PATTERNS: list[dict] = [
    # Dependency conflicts (pip, npm, etc.)
    {
        "id": "pip_no_matching_distribution",
        "class": "dependency_conflict",
        "prior": 0.9,
        "regex": r"No matching distribution found for ([\w\-\.]+==?[\w\-\.]+)",
        "sources": ["log"],
    },
    {
        "id": "pip_conflict",
        "class": "dependency_conflict",
        "prior": 0.85,
        "regex": r"(?i)ERROR.*cannot install|version (?:conflict|mismatch)",
        "sources": ["log"],
    },
    {
        "id": "npm_err_resolve",
        "class": "dependency_conflict",
        "prior": 0.85,
        "regex": r"npm ERR! (?:ERESOLVE|peer dep|Cannot resolve dependency)",
        "sources": ["log"],
    },
    # Syntax / code regressions
    {
        "id": "python_syntax_error",
        "class": "code_regression",
        "prior": 0.95,
        "regex": r"SyntaxError:.+",
        "sources": ["log"],
    },
    {
        "id": "python_import_error",
        "class": "code_regression",
        "prior": 0.8,
        "regex": r"(?:ModuleNotFoundError|ImportError):\s*.+",
        "sources": ["log"],
    },
    # Test failures
    {
        "id": "pytest_assertion",
        "class": "flaky_test",          # Could be regression; Claude disambiguates
        "prior": 0.6,
        "regex": r"(?m)^(FAILED|ERROR)\s+(\S+)",
        "sources": ["log"],
    },
    {
        "id": "pytest_failed_summary",
        "class": "code_regression",
        "prior": 0.7,
        "regex": r"=+ short test summary info =+",
        "sources": ["log"],
    },
    # Config drift
    {
        "id": "action_version_unsupported",
        "class": "config_drift",
        "prior": 0.85,
        "regex": r"Version \S+ (?:is not available|is not supported|was not found)",
        "sources": ["log"],
    },
    {
        "id": "missing_env_var",
        "class": "config_drift",
        "prior": 0.75,
        "regex": r"(?i)(?:environment variable|env var)\s+\w+\s+(?:is not set|not found|missing)",
        "sources": ["log"],
    },
    # Resource
    {
        "id": "oom_killed",
        "class": "resource_exhaustion",
        "prior": 0.9,
        "regex": r"(?i)(?:out of memory|killed.*signal 9|oom.killer)",
        "sources": ["log"],
    },
    {
        "id": "timeout",
        "class": "resource_exhaustion",
        "prior": 0.8,
        "regex": r"(?i)(?:timed out|timeout|execution deadline exceeded|exit code 124)",
        "sources": ["log"],
    },
    # Infrastructure
    {
        "id": "network_error",
        "class": "infrastructure_error",
        "prior": 0.7,
        "regex": r"(?i)(?:connection refused|could not resolve host|network is unreachable|503 service unavailable)",
        "sources": ["log"],
    },
]

class RuleDetector:
    def detect(self, ctx: FailureContext) -> list[Candidate]:
        candidates = []
        full_log = "\n".join(f"{l.step}: {l.message}" for l in ctx.logs)

        for pat in PATTERNS:
            for match in re.finditer(pat["regex"], full_log):
                candidates.append(Candidate(
                    failure_class=pat["class"],
                    confidence_prior=pat["prior"],
                    evidence_locations=[f"log:{pat['id']}"],
                    snippet=match.group(0)[:300],
                    rule_id=pat["id"],
                ))

        # Diff-based heuristic: requirements.txt changes hint at dep_conflict
        for hunk in ctx.diff_hunks:
            if hunk.file_path in ("requirements.txt", "package.json", "Cargo.toml", "pyproject.toml"):
                if hunk.new_lines:
                    candidates.append(Candidate(
                        failure_class="dependency_conflict",
                        confidence_prior=0.55,
                        evidence_locations=[f"diff:{hunk.file_path}"],
                        snippet="\n".join(hunk.new_lines[:10]),
                        rule_id="diff_dep_file_changed",
                    ))

        # Deduplicate: keep highest-prior per (class, rule_id) pair
        seen = {}
        for c in candidates:
            key = (c.failure_class, c.rule_id)
            if key not in seen or c.confidence_prior > seen[key].confidence_prior:
                seen[key] = c
        return list(seen.values())
```

### 2.3 Layer 2: Graph Centrality Scoring

```python
# app/detection/hybrid.py
import networkx as nx
from app.detection.rules import RuleDetector, Candidate
from app.graph.builder import FailureGraph
from app.models.failure import FailureContext

class HybridDetector:
    def __init__(self):
        self.rules = RuleDetector()
        self.graph_builder = FailureGraph()

    def detect(self, ctx: FailureContext, top_k: int = 5) -> list[Candidate]:
        # Layer 1: rule-based candidates
        candidates = self.rules.detect(ctx)

        # Layer 2: graph centrality weighting
        graph = self.graph_builder.build(ctx)
        scores = self._centrality_weights(graph)

        # Reweight candidate priors by connecting them to graph nodes
        enriched = []
        for c in candidates:
            bonus = 0.0
            # If candidate mentions a file from diff, boost by centrality of that file node
            for loc in c.evidence_locations:
                if loc.startswith("diff:"):
                    file_path = loc.split(":", 1)[1]
                    node_id = f"file:{file_path}"
                    if node_id in scores:
                        bonus = max(bonus, scores[node_id] * 0.2)
            c.confidence_prior = min(1.0, c.confidence_prior + bonus)
            enriched.append(c)

        # Sort by final prior, take top-K
        enriched.sort(key=lambda x: x.confidence_prior, reverse=True)
        return enriched[:top_k]

    @staticmethod
    def _centrality_weights(graph: nx.DiGraph) -> dict:
        if graph.number_of_nodes() == 0:
            return {}
        undirected = graph.to_undirected()
        return nx.betweenness_centrality(undirected)
```

### 2.4 Layer 3: Claude as Final Judge

Claude receives only the top-5 candidates + context, not the full raw logs. This keeps prompts small and signal-dense.

See Section 4 for prompt templates.

---

## 3. LLM Orchestrator (End-to-End Pipeline)

```python
# app/llm/orchestrator.py
import json
import time
import uuid
from datetime import datetime, timezone
from app.detection.hybrid import HybridDetector
from app.llm.client import claude
from app.llm.prompts import RCA_SYSTEM_PROMPT, build_user_prompt
from app.models.failure import FailureContext
from app.models.rca import RCAReport
from app.storage.vector import vector_store
from app.storage.db import get_session
from app.storage.models import FailureRow, RCARow

class RCAOrchestrator:
    def __init__(self):
        self.detector = HybridDetector()

    async def process(self, ctx: FailureContext) -> RCAReport:
        start = time.perf_counter()

        # 1. Hybrid detection produces candidates
        candidates = self.detector.detect(ctx, top_k=5)

        # 2. Retrieve similar past failures from ChromaDB
        query_text = self._failure_signature(ctx)
        similar = vector_store.similar(query_text, k=3)

        # 3. Build prompt
        user_prompt = build_user_prompt(ctx, candidates, similar)

        # 4. Call Claude with structured output
        report: RCAReport = await claude.generate_json(
            system=RCA_SYSTEM_PROMPT,
            user=user_prompt,
            schema_model=RCAReport,
            max_tokens=2048,
        )

        report.failure_id = ctx.id
        report.generated_at = datetime.now(timezone.utc).isoformat()
        report.latency_ms = int((time.perf_counter() - start) * 1000)
        report.similar_past_failures = [s["id"] for s in similar]

        # 5. Persist
        await self._persist(ctx, report)

        # 6. Index in ChromaDB for future retrieval
        vector_store.add(
            failure_id=ctx.id,
            summary_text=f"{report.summary}\n\n{self._failure_signature(ctx)}",
            metadata={
                "failure_class": report.hypotheses[0].failure_class if report.hypotheses else "unknown",
                "repo": ctx.repo_full_name,
                "timestamp": ctx.triggered_at.isoformat(),
            },
        )

        return report

    @staticmethod
    def _failure_signature(ctx: FailureContext) -> str:
        """Concise text used for similarity retrieval."""
        error_lines = [l.message for l in ctx.logs if l.level == "error"][:5]
        changed_files = [f.file_path for f in ctx.diff_hunks][:5]
        return (
            f"Repo: {ctx.repo_full_name} | "
            f"Job: {ctx.job_name} | "
            f"Errors: {' | '.join(error_lines)} | "
            f"Changed: {', '.join(changed_files)}"
        )

    @staticmethod
    async def _persist(ctx: FailureContext, report: RCAReport):
        async with get_session() as session:
            fr = FailureRow(
                id=ctx.id,
                provider=ctx.provider,
                repo_full_name=ctx.repo_full_name,
                workflow_name=ctx.workflow_name,
                job_name=ctx.job_name,
                run_id=ctx.run_id,
                run_url=ctx.run_url,
                conclusion=ctx.conclusion,
                triggered_at=ctx.triggered_at,
                completed_at=ctx.completed_at,
                duration_seconds=ctx.duration_seconds,
                context_json=ctx.model_dump(mode="json"),
            )
            session.add(fr)
            rr = RCARow(
                id=str(uuid.uuid4()),
                failure_id=ctx.id,
                generated_at=datetime.now(timezone.utc),
                summary=report.summary,
                hypotheses_json=[h.model_dump() for h in report.hypotheses],
                recommended_remediation=report.recommended_remediation.model_dump(),
                similar_past_failures=report.similar_past_failures,
                latency_ms=report.latency_ms,
                top1_class=report.hypotheses[0].failure_class if report.hypotheses else "unknown",
            )
            session.add(rr)
            await session.commit()
```

---

## 4. Prompt Engineering

### 4.1 System Prompt (RCA Generation)

```python
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
```

### 4.2 User Prompt Builder

```python
# app/llm/prompts.py (continued)
from app.models.failure import FailureContext
from app.detection.rules import Candidate

def build_user_prompt(
    ctx: FailureContext,
    candidates: list[Candidate],
    similar_failures: list[dict],
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

Produce the RCA JSON per the schema in your system prompt. Set failure_id="{ctx.id}".
"""
```

### 4.3 Few-Shot Example (Optional Boost)

Add this to the system prompt if you find quality dropping:

```
EXAMPLE (illustrative only):

INPUT SUMMARY: requirements.txt changed, log shows "No matching distribution found for requests==99.99.99"

OUTPUT:
{
  "failure_id": "example",
  "generated_at": "2026-01-01T00:00:00Z",
  "hypotheses": [
    {
      "rank": 1,
      "title": "Non-existent dependency version in requirements.txt",
      "description": "The commit bumped requests to version 99.99.99, which does not exist on PyPI. pip install aborts on the dependency resolution step, causing the build to fail before any tests run.",
      "failure_class": "dependency_conflict",
      "confidence": 0.95,
      "evidence": [
        {"source": "log", "location": "logs:Install dependencies",
         "snippet": "ERROR: No matching distribution found for requests==99.99.99",
         "relevance_score": 1.0},
        {"source": "diff", "location": "diff:requirements.txt",
         "snippet": "- requests==2.31.0\n+ requests==99.99.99",
         "relevance_score": 1.0}
      ]
    }
  ],
  "recommended_remediation": {
    "action": "Revert requests to a valid version",
    "rationale": "Version 99.99.99 does not exist. Pin to the last known-good version, 2.31.0.",
    "commands": ["sed -i 's/requests==99.99.99/requests==2.31.0/' requirements.txt",
                 "git add requirements.txt && git commit -m 'fix: pin requests to 2.31.0'"],
    "risk_level": "low"
  },
  "summary": "Build failed because requests==99.99.99 does not exist on PyPI; pin to 2.31.0.",
  "latency_ms": 0,
  "similar_past_failures": []
}
```

---

## 5. Evaluation Methodology

### 5.1 Why Real Failures, Not Synthetic

You pushed back on synthetic-only evaluation and you were right. Synthetic scenarios risk looking like "pattern recognition on known templates." Real GitHub Actions failures with real logs, real diffs, and real API responses prove the engine works on actual data.

### 5.2 Dataset: 3–5 Pre-Seeded Real Failures

Each of the failure classes from Doc 3 Section 9 becomes one evaluation case. You trigger the failure in the test repo, let GitHub Actions produce real output, the webhook fires, and the engine processes it. You label the ground truth manually based on what you *intentionally* broke.

| Case ID | Branch | Failure Class (Ground Truth) | Expected Top Hypothesis |
|---|---|---|---|
| `eval-01` | `failure-dep-conflict` | `dependency_conflict` | "`requests==99.99.99` unavailable" |
| `eval-02` | `failure-syntax-error` | `code_regression` | "SyntaxError in app.py" |
| `eval-03` | `failure-test-assertion` | `code_regression` | "`multiply` implementation changed" |
| `eval-04` | `failure-config-drift` | `config_drift` | "Python 2.7 unsupported in setup-python@v5" |
| `eval-05` | `failure-resource` | `resource_exhaustion` | "Step timed out (exit 124)" |

### 5.3 Metrics

**Top-1 Accuracy**
```
top1_correct = count(cases where report.hypotheses[0].failure_class == ground_truth)
top1_accuracy = top1_correct / total_cases
Target: ≥ 0.7 (3/5 = 0.6 is floor; 4/5 = 0.8 is strong)
```

**Top-3 Accuracy**
```
top3_correct = count(cases where ground_truth in [h.failure_class for h in report.hypotheses[:3]])
top3_accuracy = top3_correct / total_cases
Target: ≥ 0.9 (at minimum 4/5, ideally 5/5)
```

**Mean Time to Diagnosis (MTTD)**
```
mttd_ms = mean(report.latency_ms for all cases)
Target: < 15000 ms (15 seconds)
```

**Evidence Precision (Manual Review)**
For each hypothesis, count evidence snippets that actually support the hypothesis vs. hallucinated/irrelevant ones.
```
precision = (relevant evidence) / (total evidence)
Target: ≥ 0.8
```

### 5.4 Evaluation Harness Code

```python
# app/evaluation/metrics.py
from datetime import datetime
from sqlalchemy import select
from app.storage.db import get_session
from app.storage.models import RCARow, MetricsSnapshotRow

GROUND_TRUTH: dict[str, str] = {
    # populated by seed script — maps failure_id to expected failure_class
}

async def compute_metrics() -> dict:
    async with get_session() as session:
        rcas = (await session.execute(
            select(RCARow).where(RCARow.ground_truth_class.isnot(None))
        )).scalars().all()

        if not rcas:
            return {
                "top1_accuracy": None,
                "top3_accuracy": None,
                "mttd_ms": None,
                "sample_size": 0,
                "note": "No labeled cases yet",
            }

        top1_correct = 0
        top3_correct = 0
        latencies = []
        for r in rcas:
            hyp_classes = [h["failure_class"] for h in r.hypotheses_json]
            if hyp_classes and hyp_classes[0] == r.ground_truth_class:
                top1_correct += 1
            if r.ground_truth_class in hyp_classes[:3]:
                top3_correct += 1
            latencies.append(r.latency_ms)

        n = len(rcas)
        metrics = {
            "top1_accuracy": round(top1_correct / n, 3),
            "top3_accuracy": round(top3_correct / n, 3),
            "mttd_ms": int(sum(latencies) / n),
            "sample_size": n,
        }

        # Snapshot for history
        session.add(MetricsSnapshotRow(
            timestamp=datetime.utcnow(),
            top1_accuracy=metrics["top1_accuracy"],
            top3_accuracy=metrics["top3_accuracy"],
            mttd_ms=metrics["mttd_ms"],
            sample_size=n,
        ))
        await session.commit()
        return metrics
```

### 5.5 Metrics Endpoint

```python
# app/routers/metrics.py
from fastapi import APIRouter
from app.evaluation.metrics import compute_metrics

router = APIRouter(prefix="/metrics", tags=["metrics"])

@router.get("")
async def get_metrics():
    return await compute_metrics()
```

### 5.6 Labeling Ground Truth

After seeding each failure by pushing one of the pre-crafted commits (Doc 3 Section 9), label it:

```python
# Partner A runs this once per seeded failure, via an admin endpoint or script
async def label_ground_truth(failure_id: str, true_class: str):
    async with get_session() as session:
        rca = (await session.execute(
            select(RCARow).where(RCARow.failure_id == failure_id)
        )).scalar_one()
        rca.ground_truth_class = true_class
        await session.commit()
```

Wire it as `POST /eval/label` with `{failure_id, true_class}` if useful for demo control.

### 5.7 Evaluation Execution Flow (Hours 13–15)

```
┌─────────────────────────────────────────────────────────────┐
│                 EVALUATION EXECUTION FLOW                   │
└─────────────────────────────────────────────────────────────┘

 1. Partner A creates 5 failure branches in test repo (one per class)
      │
      ▼
 2. For each branch:
      a. Merge branch to main → triggers GitHub Actions
      b. Actions fails → webhook fires → engine processes
      c. RCA stored in SQLite
      d. Partner A calls POST /eval/label with ground truth class
      e. Revert the bad commit, reset main
      │
      ▼
 3. Partner A calls GET /metrics
      │
      ▼
 4. Results appear on dashboard metrics panel
      │
      ▼
 5. If accuracy below target: tune prompts, adjust rule priors,
    re-run the affected cases
      │
      ▼
 6. Final metrics locked at ~Hour 15
```

---

## 6. "Learns Over Time" Mechanism

### 6.1 The Narrative (For Judges)

> "Every RCA we generate gets indexed in ChromaDB. When a new failure comes in, we retrieve the 3 most semantically-similar past failures and include them in Claude's context. This means PipelineIQ gets *measurably better* as it processes more failures — institutional memory that doesn't depend on any one engineer."

### 6.2 Concrete Mechanism

1. After each RCA is generated, we embed its summary + failure signature and store in ChromaDB along with metadata (failure class, repo, timestamp).
2. On the next failure, we embed the new failure's signature and query Chroma for top-3 nearest neighbors.
3. We pass those 3 past summaries in Claude's user prompt as context.
4. Claude uses them as prior evidence — if the same dependency broke last week, confidence on the diagnosis increases.

### 6.3 Demonstrating It Live

During Hour 14, pre-seed Chroma with a few "historical" failures (reuse your eval cases). Then during demo, trigger a similar failure and point to the "Similar Past Failures" panel on the dashboard showing retrieved cases. This makes the learning tangible visually.

---

## 7. Prompt Iteration Protocol

Not every prompt works first try. Hours 15–16 should be prompt tuning.

| Symptom | Fix |
|---|---|
| Claude returns prose before/after JSON | Strengthen: "Respond ONLY with JSON. Do not add any prose, commentary, or code fences." |
| Malformed JSON | Add `generate_json` retry with "fix your JSON" prompt (already in code) |
| Hypothesis confidences all 0.95+ (overconfident) | Add: "Calibrate your confidence. Use 0.9+ only when evidence is unambiguous. Use 0.6–0.8 for likely-but-not-certain." |
| Evidence snippets invented, not in input | Emphasize: "Quote exact text from the provided input. Never paraphrase or invent." |
| Wrong failure_class chosen | Add concrete example of the class being confused (few-shot) |
| Remediation too generic | Add: "Remediation must include specific file paths, version numbers, or commands — never 'review the code' or 'check logs'." |

---

## 8. Cost & Latency Monitoring

```python
# Log each Claude call's tokens/latency to SQLite for post-hackathon analysis
# (optional but nice for the "metrics beyond accuracy" slide)
```

Add `input_tokens`, `output_tokens`, `duration_ms` columns to `RCARow` if you want to report cost per RCA during the demo. Judges often ask "what does this cost at scale?"

Rough math: $0.003 per 1K input tokens + $0.015 per 1K output tokens for Sonnet 4.5 → ~$0.04 per RCA → ~$40 per 1000 failures. Compare to the 2–6 engineer-hours saved per failure.

---

## 9. Failure Modes of the System Itself

Acknowledge openly in the demo/slides:

| System Failure Mode | Likelihood | Handling |
|---|---|---|
| Claude hallucinates wrong class | Medium | Rule-based prior + validation; Top-3 metric as safety net |
| Claude returns malformed JSON | Low | Auto-retry with fix prompt; graceful 500 error to dashboard |
| Rate limit mid-demo | Low | Pre-cache seeded failure RCAs; exponential backoff |
| Webhook signature mismatch | Low | Reject with 401; surface clearly in logs |
| Logs too large for prompt window | Medium | Smart truncation (error-adjacent windowing); already implemented |
| No rule matches novel failure | Medium | Claude still reasons; confidence naturally lower |

---

## 10. Evaluation Flow Infographic

```
┌──────────────────────────────────────────────────────────────────┐
│            Evaluation Loop — Per Failure Case                    │
│                                                                  │
│   ┌──────────┐                                                   │
│   │ Push bad │                                                   │
│   │  commit  │                                                   │
│   └────┬─────┘                                                   │
│        ▼                                                         │
│   ┌──────────┐      ┌──────────┐      ┌──────────┐               │
│   │  GitHub  │─────►│ Webhook  │─────►│ Ingest & │               │
│   │  Actions │ fail │  fires   │      │ Normalize│               │
│   └──────────┘      └──────────┘      └────┬─────┘               │
│                                            ▼                     │
│                                       ┌──────────┐               │
│                                       │ Hybrid   │               │
│                                       │ Detect   │               │
│                                       │  Layer 1 │               │
│                                       │   Rules  │               │
│                                       └────┬─────┘               │
│                                            ▼                     │
│                                       ┌──────────┐               │
│                                       │  Layer 2 │               │
│                                       │   Graph  │               │
│                                       │Centrality│               │
│                                       └────┬─────┘               │
│                                            ▼                     │
│                                       ┌──────────┐               │
│                                       │  Layer 3 │               │
│                                       │  Claude  │◄──Chroma RAG  │
│                                       │ Reasoning│               │
│                                       └────┬─────┘               │
│                                            ▼                     │
│                                       ┌──────────┐               │
│                                       │   RCA    │               │
│                                       │  Report  │               │
│                                       └────┬─────┘               │
│                                            ▼                     │
│        ┌──────────┐ label           ┌──────────┐                 │
│        │Partner A │─────────────────►│ Ground  │                 │
│        │  Labels  │                 │  Truth  │                  │
│        └──────────┘                 └────┬─────┘                 │
│                                          ▼                       │
│                                     ┌──────────┐                 │
│                                     │ Metrics  │                 │
│                                     │Top-1/3/  │                 │
│                                     │  MTTD    │                 │
│                                     └────┬─────┘                 │
│                                          ▼                       │
│                                     ┌──────────┐                 │
│                                     │Dashboard │                 │
│                                     │ Display  │                 │
│                                     └──────────┘                 │
└──────────────────────────────────────────────────────────────────┘
```

---

**Next Document**: [05_STEP_BY_STEP_GUIDE.md](./05_STEP_BY_STEP_GUIDE.md)
