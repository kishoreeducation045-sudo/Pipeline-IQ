# app/models/failure.py
from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime

class LogLine(BaseModel):
    timestamp: Optional[datetime] = None
    step: str                                   # e.g. "Install dependencies"
    level: Literal["info", "warning", "error"] = "info"
    message: str

class DiffHunk(BaseModel):
    file_path: str
    old_lines: list[str]
    new_lines: list[str]
    change_type: Literal["added", "modified", "deleted"]

class TestResult(BaseModel):
    name: str
    passed: bool
    duration_ms: Optional[int] = None
    failure_message: Optional[str] = None

class CommitInfo(BaseModel):
    sha: str
    author: str
    message: str
    timestamp: datetime
    files_changed: list[str]

class FailureContext(BaseModel):
    """Unified schema — all providers normalize to this."""
    id: str = Field(description="Internal UUID")
    provider: Literal["github", "gitlab"]
    repo_full_name: str                         # e.g. "user/repo"
    workflow_name: str                          # e.g. "CI"
    job_name: str                               # e.g. "build-and-test"
    run_id: str                                 # Provider's run ID
    run_url: str                                # Clickable link to provider UI
    conclusion: Literal["failure", "cancelled", "timed_out"]
    triggered_at: datetime
    completed_at: datetime
    duration_seconds: int

    head_commit: CommitInfo
    recent_commits: list[CommitInfo] = []       # Last 5 commits for context

    logs: list[LogLine]
    diff_hunks: list[DiffHunk]
    test_results: list[TestResult] = []

    raw_payload: dict                           # Keep original for debugging
