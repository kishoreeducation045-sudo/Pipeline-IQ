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
