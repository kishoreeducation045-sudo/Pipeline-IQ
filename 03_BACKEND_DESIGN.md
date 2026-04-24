# PipelineIQ — Backend Design Specification

**Document 3 of 4** · Modules, data ingestion, graph schema, FastAPI contracts, complete copy-paste code

---

## 1. Module Breakdown

Every Python module in the backend, its responsibility, and key classes/functions.

| Module | File | Responsibility | Key Symbols |
|---|---|---|---|
| Entry point | `app/main.py` | FastAPI instantiation, router mounting, lifespan | `app`, `lifespan()` |
| Config | `app/config.py` | Env var parsing via Pydantic Settings | `Settings` |
| Models | `app/models/failure.py` | Failure schema | `FailureContext`, `LogLine`, `DiffHunk` |
| Models | `app/models/rca.py` | RCA schema | `RCAReport`, `Hypothesis`, `Evidence`, `Remediation` |
| Models | `app/models/graph.py` | Graph schema | `NodeType`, `EdgeType`, `GraphNode`, `GraphEdge` |
| Router | `app/routers/webhooks.py` | Webhook endpoints | `POST /webhook/github`, `POST /webhook/gitlab` |
| Router | `app/routers/failures.py` | Failure + RCA endpoints | `GET /failures`, `GET /failures/{id}` |
| Router | `app/routers/metrics.py` | Eval metrics | `GET /metrics` |
| Ingestion | `app/ingestion/github.py` | GitHub API client | `GitHubIngestor.fetch_context()` |
| Ingestion | `app/ingestion/gitlab.py` | GitLab stub | `GitLabIngestor.fetch_context()` |
| Normalizer | `app/normalizer/normalizer.py` | Provider payload → unified schema | `normalize_github()`, `normalize_gitlab()` |
| Graph | `app/graph/builder.py` | Build NetworkX failure graph | `FailureGraph.build()` |
| Graph | `app/graph/store.py` | Abstract GraphStore interface | `GraphStore` (ABC), `NetworkXStore` |
| Detection | `app/detection/rules.py` | Rule-based pattern matchers | `RuleDetector`, `PATTERNS` |
| Detection | `app/detection/centrality.py` | Graph centrality ranking | `CentralityRanker.rank()` |
| Detection | `app/detection/hybrid.py` | Combines layers 1+2 to produce candidates | `HybridDetector.detect()` |
| LLM | `app/llm/client.py` | Anthropic SDK wrapper | `ClaudeClient.generate_rca()` |
| LLM | `app/llm/prompts.py` | Prompt templates | `RCA_SYSTEM_PROMPT`, `build_user_prompt()` |
| LLM | `app/llm/orchestrator.py` | End-to-end RCA pipeline | `RCAOrchestrator.process()` |
| Storage | `app/storage/db.py` | SQLite via SQLAlchemy | `engine`, `get_session()` |
| Storage | `app/storage/vector.py` | ChromaDB wrapper | `VectorStore.add()`, `VectorStore.similar()` |
| WS | `app/ws/manager.py` | WebSocket connection manager | `ConnectionManager` |
| Eval | `app/evaluation/seed.py` | Seed real failures with ground truth | `seed_failures()` |
| Eval | `app/evaluation/metrics.py` | Compute Top-1, Top-3, MTTD | `compute_metrics()` |

---

## 2. Unified Data Schema (Pydantic Models)

### 2.1 FailureContext — What Comes In After Normalization

```python
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
```

### 2.2 RCAReport — What Claude Generates

```python
# app/models/rca.py
from pydantic import BaseModel, Field
from typing import Literal

class Evidence(BaseModel):
    source: Literal["log", "diff", "test", "commit"]
    location: str                               # e.g. "logs:line 42" or "diff:requirements.txt"
    snippet: str                                # Actual text
    relevance_score: float = Field(ge=0, le=1)

class Hypothesis(BaseModel):
    rank: int = Field(ge=1, le=5)
    title: str                                  # Short headline
    description: str                            # 2-3 sentence explanation
    failure_class: Literal[
        "dependency_conflict",
        "flaky_test",
        "config_drift",
        "resource_exhaustion",
        "code_regression",
        "infrastructure_error",
        "unknown"
    ]
    confidence: float = Field(ge=0, le=1)
    evidence: list[Evidence]

class Remediation(BaseModel):
    action: str                                 # e.g. "Pin requests dependency"
    rationale: str
    commands: list[str] = []                    # e.g. ["pip install requests==2.31.0"]
    risk_level: Literal["low", "medium", "high"]

class RCAReport(BaseModel):
    failure_id: str
    generated_at: str                           # ISO 8601
    hypotheses: list[Hypothesis]                # Ranked, max 3
    recommended_remediation: Remediation
    summary: str                                # 1-sentence human summary
    latency_ms: int                             # How long Claude took
    similar_past_failures: list[str] = []       # IDs of retrieved past cases
```

---

## 3. Failure Correlation Graph Schema

The graph represents relationships between artifacts that are candidates for root-cause reasoning.

### 3.1 Node Types

| Node Type | Represents | Key Attributes |
|---|---|---|
| `Commit` | Git commit | `sha`, `author`, `message`, `timestamp` |
| `File` | Source file | `path`, `language` |
| `Test` | Individual test | `name`, `passed`, `failure_message` |
| `Dependency` | Package/library | `name`, `version`, `ecosystem` (pip, npm) |
| `PipelineStep` | Job step | `name`, `status`, `duration_ms` |
| `ConfigFile` | CI/env config | `path`, `type` (yaml, env, toml) |

### 3.2 Edge Types

| Edge | From → To | Semantics |
|---|---|---|
| `MODIFIES` | Commit → File | Commit changed this file |
| `INTRODUCES` | Commit → Dependency | Commit added/changed this dep |
| `TESTS` | Test → File | Test exercises this file |
| `DEPENDS_ON` | File → Dependency | File imports this dep |
| `TRIGGERS` | Commit → PipelineStep | Commit's push ran this step |
| `FAILS_IN` | Test → PipelineStep | Test failed in this step |
| `CONFIGURES` | ConfigFile → PipelineStep | Config controls this step |

### 3.3 Visualization

```
                      ┌──────────────┐
                      │   Commit     │ (HEAD of failing build)
                      │   abc123     │
                      └───┬──────────┘
          MODIFIES        │         INTRODUCES
          ┌───────────────┼─────────────────────┐
          ▼               ▼                     ▼
    ┌──────────┐    ┌──────────┐          ┌──────────────┐
    │ File     │    │ File     │          │ Dependency   │
    │ app.py   │    │ reqs.txt │          │ requests@3.0 │
    └─────┬────┘    └──────────┘          └──────┬───────┘
          │TESTS                                 │
          ▼                              DEPENDS_ON
    ┌──────────┐                                 │
    │ Test     │                                 │
    │ test_api │ ◄───── FAILS_IN ──── ┌──────────┴──────┐
    └──────────┘                      │ PipelineStep    │
                                      │ "Install deps"  │
                                      └─────────────────┘
```

### 3.4 NetworkX Implementation

```python
# app/graph/builder.py
import networkx as nx
from app.models.failure import FailureContext

class FailureGraph:
    def __init__(self):
        self.graph = nx.DiGraph()

    def build(self, ctx: FailureContext) -> nx.DiGraph:
        g = nx.DiGraph()
        commit = ctx.head_commit

        # Commit node
        g.add_node(f"commit:{commit.sha}",
                   type="Commit",
                   sha=commit.sha,
                   author=commit.author,
                   message=commit.message)

        # File nodes + MODIFIES edges
        for file_path in commit.files_changed:
            file_id = f"file:{file_path}"
            g.add_node(file_id, type="File", path=file_path)
            g.add_edge(f"commit:{commit.sha}", file_id, type="MODIFIES")

            # Detect dependency file changes (INTRODUCES dep)
            if file_path in ("requirements.txt", "package.json", "Cargo.toml", "pyproject.toml"):
                for hunk in ctx.diff_hunks:
                    if hunk.file_path == file_path:
                        for line in hunk.new_lines:
                            dep = self._parse_dep(line, file_path)
                            if dep:
                                dep_id = f"dep:{dep['name']}@{dep['version']}"
                                g.add_node(dep_id, type="Dependency", **dep)
                                g.add_edge(f"commit:{commit.sha}", dep_id, type="INTRODUCES")

        # PipelineStep nodes (derive from logs)
        steps = {line.step for line in ctx.logs}
        for step in steps:
            step_id = f"step:{step}"
            error_lines = [l for l in ctx.logs if l.step == step and l.level == "error"]
            status = "failed" if error_lines else "passed"
            g.add_node(step_id, type="PipelineStep", name=step, status=status)
            g.add_edge(f"commit:{commit.sha}", step_id, type="TRIGGERS")

        # Test nodes + FAILS_IN edges
        for test in ctx.test_results:
            test_id = f"test:{test.name}"
            g.add_node(test_id, type="Test", name=test.name, passed=test.passed,
                       failure_message=test.failure_message)
            if not test.passed:
                # Assume tests ran in a "test" step; refine with actual step mapping
                failing_steps = [n for n, d in g.nodes(data=True)
                                 if d.get("type") == "PipelineStep" and d.get("status") == "failed"]
                for step_id in failing_steps:
                    g.add_edge(test_id, step_id, type="FAILS_IN")

        self.graph = g
        return g

    @staticmethod
    def _parse_dep(line: str, filename: str) -> dict | None:
        """Very simple parser — good enough for prototype."""
        line = line.strip()
        if filename == "requirements.txt" and "==" in line:
            name, _, version = line.partition("==")
            return {"name": name.strip(), "version": version.strip(), "ecosystem": "pip"}
        # Add npm/cargo parsing as needed
        return None
```

### 3.5 Graph Centrality for Ranking

```python
# app/detection/centrality.py
import networkx as nx

class CentralityRanker:
    def rank(self, graph: nx.DiGraph) -> list[tuple[str, float]]:
        """Return nodes ranked by betweenness centrality, highest first."""
        if graph.number_of_nodes() == 0:
            return []
        undirected = graph.to_undirected()
        scores = nx.betweenness_centrality(undirected)
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

Betweenness centrality identifies nodes that sit on many shortest paths — in failure graphs, these are typically the "blast radius" hubs (e.g., a dependency used by many files whose tests then fail).

---

## 4. FastAPI Endpoint Contracts

### 4.1 Endpoint Summary

| Method | Path | Purpose | Request | Response |
|---|---|---|---|---|
| GET | `/health` | Liveness probe | — | `{"status": "ok"}` |
| POST | `/webhook/github` | GitHub Actions webhook | GitHub payload | `{"accepted": true, "failure_id": "..."}` |
| POST | `/webhook/gitlab` | GitLab stub | GitLab payload | `{"accepted": true, "note": "GitLab adapter: stub"}` |
| GET | `/failures` | List recent failures | `?limit=20` | `FailureSummary[]` |
| GET | `/failures/{id}` | Detailed RCA | — | `FailureDetail` |
| GET | `/failures/{id}/remediation` | Just the remediation | — | `Remediation` |
| GET | `/metrics` | Eval metrics | — | `{top1_accuracy, top3_accuracy, mttd_ms, ...}` |
| WS | `/ws/live` | Live dashboard updates | — | Broadcasts `FailureEvent` |
| POST | `/eval/seed` | (dev) seed failures | — | `{"seeded": 5}` |
| POST | `/eval/run` | (dev) run eval harness | — | Metrics |

### 4.2 Webhook Handler (Full Code)

```python
# app/routers/webhooks.py
import hmac
import hashlib
import uuid
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Header
from app.config import settings
from app.ingestion.github import GitHubIngestor
from app.ingestion.gitlab import GitLabIngestor
from app.llm.orchestrator import RCAOrchestrator
from app.ws.manager import manager

router = APIRouter(prefix="/webhook", tags=["webhooks"])

def verify_github_signature(body: bytes, signature: str | None) -> bool:
    if not signature or not settings.github_webhook_secret:
        return False
    mac = hmac.new(
        settings.github_webhook_secret.encode(),
        msg=body,
        digestmod=hashlib.sha256,
    )
    expected = f"sha256={mac.hexdigest()}"
    return hmac.compare_digest(expected, signature)

@router.post("/github")
async def github_webhook(
    request: Request,
    background: BackgroundTasks,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
):
    body = await request.body()
    if not verify_github_signature(body, x_hub_signature_256):
        raise HTTPException(401, "Invalid signature")
    payload = await request.json()

    # Only handle workflow_run completed events with failure
    if x_github_event != "workflow_run":
        return {"accepted": False, "reason": "not workflow_run"}
    run = payload.get("workflow_run", {})
    if run.get("status") != "completed" or run.get("conclusion") not in ("failure", "timed_out", "cancelled"):
        return {"accepted": False, "reason": "not a failed completed run"}

    failure_id = str(uuid.uuid4())
    background.add_task(process_github_failure, failure_id, payload)
    return {"accepted": True, "failure_id": failure_id}

async def process_github_failure(failure_id: str, payload: dict):
    ingestor = GitHubIngestor()
    ctx = await ingestor.fetch_context(failure_id, payload)
    orchestrator = RCAOrchestrator()
    rca = await orchestrator.process(ctx)
    await manager.broadcast({"type": "rca_ready", "failure_id": failure_id, "summary": rca.summary})

@router.post("/gitlab")
async def gitlab_webhook(request: Request):
    payload = await request.json()
    # Stub — log and return. Full integration deferred.
    return {
        "accepted": True,
        "note": "GitLab adapter: stub (full integration in production roadmap)",
        "payload_keys": list(payload.keys()),
    }
```

### 4.3 Failures List/Detail Endpoints

```python
# app/routers/failures.py
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, desc
from app.storage.db import get_session
from app.storage.models import FailureRow, RCARow
from app.models.rca import RCAReport

router = APIRouter(prefix="/failures", tags=["failures"])

@router.get("")
async def list_failures(limit: int = Query(default=20, le=100)):
    async with get_session() as session:
        rows = (await session.execute(
            select(FailureRow).order_by(desc(FailureRow.triggered_at)).limit(limit)
        )).scalars().all()
        return [
            {
                "id": r.id,
                "repo": r.repo_full_name,
                "workflow": r.workflow_name,
                "job": r.job_name,
                "conclusion": r.conclusion,
                "triggered_at": r.triggered_at.isoformat(),
                "has_rca": r.rca is not None,
                "summary": r.rca.summary if r.rca else None,
            }
            for r in rows
        ]

@router.get("/{failure_id}")
async def failure_detail(failure_id: str):
    async with get_session() as session:
        row = (await session.execute(
            select(FailureRow).where(FailureRow.id == failure_id)
        )).scalar_one_or_none()
        if not row:
            raise HTTPException(404, "Failure not found")
        return {
            "failure": row.to_dict(),
            "rca": row.rca.to_dict() if row.rca else None,
        }

@router.get("/{failure_id}/remediation")
async def failure_remediation(failure_id: str):
    async with get_session() as session:
        rca = (await session.execute(
            select(RCARow).where(RCARow.failure_id == failure_id)
        )).scalar_one_or_none()
        if not rca:
            raise HTTPException(404, "No RCA yet")
        return rca.recommended_remediation
```

### 4.4 WebSocket Manager

```python
# app/ws/manager.py
from fastapi import WebSocket
import asyncio

class ConnectionManager:
    def __init__(self):
        self.active: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self.active.add(ws)

    def disconnect(self, ws: WebSocket):
        self.active.discard(ws)

    async def broadcast(self, message: dict):
        dead = []
        for ws in list(self.active):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

manager = ConnectionManager()
```

### 4.5 Main Application

```python
# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import webhooks, failures, metrics
from app.storage.db import init_db
from app.ws.manager import manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="PipelineIQ", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhooks.router)
app.include_router(failures.router)
app.include_router(metrics.router)

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}

@app.websocket("/ws/live")
async def ws_live(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # Keep-alive; we broadcast, don't receive
    except Exception:
        manager.disconnect(ws)
```

---

## 5. SQLite Schema

Using SQLAlchemy async with `aiosqlite` driver.

```python
# app/storage/models.py
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, DateTime, JSON, ForeignKey, Float, Text
from datetime import datetime

class Base(DeclarativeBase):
    pass

class FailureRow(Base):
    __tablename__ = "failures"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    provider: Mapped[str] = mapped_column(String)
    repo_full_name: Mapped[str] = mapped_column(String, index=True)
    workflow_name: Mapped[str] = mapped_column(String)
    job_name: Mapped[str] = mapped_column(String)
    run_id: Mapped[str] = mapped_column(String)
    run_url: Mapped[str] = mapped_column(String)
    conclusion: Mapped[str] = mapped_column(String)
    triggered_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime)
    duration_seconds: Mapped[int] = mapped_column(Integer)
    context_json: Mapped[dict] = mapped_column(JSON)  # Full FailureContext
    rca: Mapped["RCARow"] = relationship(back_populates="failure", uselist=False)

class RCARow(Base):
    __tablename__ = "rca_reports"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    failure_id: Mapped[str] = mapped_column(String, ForeignKey("failures.id"), index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime)
    summary: Mapped[str] = mapped_column(Text)
    hypotheses_json: Mapped[list] = mapped_column(JSON)
    recommended_remediation: Mapped[dict] = mapped_column(JSON)
    similar_past_failures: Mapped[list] = mapped_column(JSON, default=list)
    latency_ms: Mapped[int] = mapped_column(Integer)
    top1_class: Mapped[str] = mapped_column(String, index=True)
    ground_truth_class: Mapped[str | None] = mapped_column(String, nullable=True)
    failure: Mapped[FailureRow] = relationship(back_populates="rca")

class MetricsSnapshotRow(Base):
    __tablename__ = "metrics_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    top1_accuracy: Mapped[float] = mapped_column(Float)
    top3_accuracy: Mapped[float] = mapped_column(Float)
    mttd_ms: Mapped[int] = mapped_column(Integer)
    sample_size: Mapped[int] = mapped_column(Integer)
```

---

## 6. ChromaDB Collection Design

```python
# app/storage/vector.py
import chromadb
from chromadb.config import Settings
from app.config import settings

class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=settings.chroma_path,
            settings=Settings(anonymized_telemetry=False),
        )
        # One collection for failure summaries; embeddings via default model
        self.collection = self.client.get_or_create_collection(
            name="failure_summaries",
            metadata={"description": "Past RCA summaries for similarity retrieval"},
        )

    def add(self, failure_id: str, summary_text: str, metadata: dict):
        self.collection.add(
            ids=[failure_id],
            documents=[summary_text],
            metadatas=[metadata],
        )

    def similar(self, query_text: str, k: int = 3) -> list[dict]:
        if self.collection.count() == 0:
            return []
        res = self.collection.query(query_texts=[query_text], n_results=min(k, self.collection.count()))
        return [
            {"id": id_, "document": doc, "metadata": meta, "distance": dist}
            for id_, doc, meta, dist in zip(
                res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0]
            )
        ]

vector_store = VectorStore()
```

---

## 7. Dockerfile and docker-compose.yml

### 7.1 `backend/Dockerfile`

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# System deps for some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management (or use pip if preferred)
COPY pyproject.toml ./
RUN pip install --no-cache-dir uv && uv pip install --system -r pyproject.toml

COPY app ./app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 7.2 `backend/pyproject.toml`

```toml
[project]
name = "pipelineiq-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "pydantic>=2.8",
    "pydantic-settings>=2.4",
    "anthropic>=0.34",
    "httpx>=0.27",
    "networkx>=3.3",
    "sqlalchemy>=2.0",
    "aiosqlite>=0.20",
    "chromadb>=0.5",
    "python-multipart>=0.0.9",
    "PyGithub>=2.3",
]
```

### 7.3 Root `docker-compose.yml`

```yaml
version: "3.9"
services:
  backend:
    build: ./backend
    container_name: pipelineiq-backend
    ports:
      - "8000:8000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - GITHUB_WEBHOOK_SECRET=${GITHUB_WEBHOOK_SECRET}
      - CLAUDE_MODEL=${CLAUDE_MODEL:-claude-sonnet-4-5}
      - SQLITE_PATH=/data/pipelineiq.db
      - CHROMA_PATH=/data/chroma
      - CORS_ORIGINS=http://localhost:5173
    volumes:
      - ./data:/data
    restart: unless-stopped
```

Run with:
```bash
docker compose up --build
```

---

## 8. Test App Repo: Complete Copy-Paste Code

This is the **entire test application**. Clone your fresh repo, paste these four files, push.

### 8.1 `app.py` (dummy Flask app)

```python
# app.py
from flask import Flask, jsonify
import requests

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({"message": "PipelineIQ test app"})

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/ping-external")
def ping_external():
    # Uses requests library — good candidate for dependency-related failures
    try:
        r = requests.get("https://httpbin.org/status/200", timeout=2)
        return jsonify({"external_status": r.status_code})
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 502

def add(a, b):
    return a + b

def multiply(a, b):
    return a * b

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

### 8.2 `requirements.txt`

```txt
flask==3.0.3
requests==2.31.0
pytest==8.3.2
```

### 8.3 `tests/test_app.py`

```python
# tests/test_app.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import app, add, multiply

def test_home():
    client = app.test_client()
    r = client.get("/")
    assert r.status_code == 200
    assert r.get_json() == {"message": "PipelineIQ test app"}

def test_health():
    client = app.test_client()
    r = client.get("/health")
    assert r.status_code == 200

def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0

def test_multiply():
    assert multiply(4, 5) == 20
    assert multiply(0, 100) == 0
```

### 8.4 `.github/workflows/ci.yml` (complete, working)

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:

jobs:
  build-and-test:
    name: Build and Test
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Cache pip
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Lint (syntax check)
        run: |
          python -m py_compile app.py
          python -m py_compile tests/test_app.py

      - name: Run tests
        run: |
          pytest tests/ -v
```

**Expected behavior:** On push, GitHub Actions runs this workflow. Green = success. Any failure triggers a webhook to your backend.

---

## 9. Pre-Crafted Failure Injection Commits (5 Types)

These are the **exact changes** to make to the test repo to trigger each failure class. Keep each on a separate branch for easy live-demo toggling.

### 9.1 Failure Class 1: Dependency Conflict

```bash
git checkout -b failure-dep-conflict
```

Edit `requirements.txt` to:

```txt
flask==3.0.3
requests==99.99.99
pytest==8.3.2
```

Commit message: `chore: bump requests (intentional break for demo)`

**Ground truth RCA:** Dependency conflict — `requests==99.99.99` does not exist on PyPI; `pip install` fails.

### 9.2 Failure Class 2: Syntax Error (Code Regression)

```bash
git checkout -b failure-syntax-error
```

Edit `app.py`, change the `add` function to:

```python
def add(a, b):
    return a +  # intentional syntax error
```

Commit message: `feat: refactor add (demo syntax break)`

**Ground truth RCA:** Code regression — syntax error in `app.py` at `add()`.

### 9.3 Failure Class 3: Flaky / Assertion Test Failure

```bash
git checkout -b failure-test-assertion
```

Edit `app.py`, change `multiply`:

```python
def multiply(a, b):
    return a + b  # wrong operation
```

Commit message: `refactor: simplify multiply logic`

**Ground truth RCA:** Code regression — `multiply()` implementation changed, `test_multiply` fails.

### 9.4 Failure Class 4: Config Drift (CI YAML Error)

```bash
git checkout -b failure-config-drift
```

Edit `.github/workflows/ci.yml`, change Python version:

```yaml
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "2.7"   # unsupported
```

Commit message: `ci: pin python version`

**Ground truth RCA:** Config drift — CI pinned to Python 2.7 which `setup-python@v5` does not support on ubuntu-latest.

### 9.5 Failure Class 5: Resource / Infra (Simulated)

```bash
git checkout -b failure-resource
```

Edit `.github/workflows/ci.yml`, add a timeout-inducing step before tests:

```yaml
      - name: Simulate resource exhaustion
        run: |
          timeout 5 bash -c 'while true; do :; done'
          exit 124
```

Commit message: `ci: add resource validation step`

**Ground truth RCA:** Resource exhaustion — step timed out, pipeline aborted.

---

## 10. GitHub Webhook Setup (Step-by-Step)

This is the linkage between your test repo and your backend.

### 10.1 Start ngrok and note your public URL

```bash
ngrok http 8000
# Output shows: Forwarding https://abc-123-456.ngrok-free.app -> http://localhost:8000
```

**Keep this terminal open.** Copy the HTTPS URL.

### 10.2 Configure the webhook on GitHub

1. Go to your test repo → **Settings** → **Webhooks** → **Add webhook**
2. Fill in:
   - **Payload URL:** `https://abc-123-456.ngrok-free.app/webhook/github`
   - **Content type:** `application/json`
   - **Secret:** use the same value you set in `.env` as `GITHUB_WEBHOOK_SECRET`
   - **SSL verification:** enabled
3. **Which events?** → Select "Let me select individual events" → check only **Workflow runs**
4. **Active:** ✓
5. Click **Add webhook**

### 10.3 Verify webhook delivery

1. GitHub UI → Webhooks → your webhook → **Recent Deliveries** tab
2. Push any commit to trigger a workflow
3. You should see a delivery with response `200 OK`
4. If `401`: signature verification failed — check `GITHUB_WEBHOOK_SECRET` matches
5. If `timeout`/`5xx`: backend not reachable — check ngrok is running and `docker compose up` succeeded

### 10.4 Generate a GitHub Personal Access Token

Backend needs this to fetch logs/diffs:

1. GitHub → **Settings** (your user) → **Developer settings** → **Personal access tokens** → **Fine-grained tokens**
2. **Generate new token**
3. Scope: only your test repo
4. Permissions needed:
   - **Contents:** Read
   - **Actions:** Read
   - **Metadata:** Read (default)
5. Generate, copy token, paste into `.env` as `GITHUB_TOKEN`

---

## 11. Synthetic-First Seed Flow (For Before the Real Repo is Ready)

During Hours 2–5 before your Partner B has the GitHub repo+Actions set up, Partner A can develop and test the RCA engine using synthetic fixtures.

```python
# app/evaluation/seed.py
from app.models.failure import FailureContext, LogLine, DiffHunk, CommitInfo
from datetime import datetime, timedelta

def synthetic_dependency_failure() -> FailureContext:
    return FailureContext(
        id="synth-dep-1",
        provider="github",
        repo_full_name="pipelineiq/testapp",
        workflow_name="CI",
        job_name="build-and-test",
        run_id="12345",
        run_url="https://github.com/pipelineiq/testapp/actions/runs/12345",
        conclusion="failure",
        triggered_at=datetime.utcnow() - timedelta(seconds=30),
        completed_at=datetime.utcnow(),
        duration_seconds=30,
        head_commit=CommitInfo(
            sha="abc123",
            author="testuser",
            message="chore: bump requests",
            timestamp=datetime.utcnow(),
            files_changed=["requirements.txt"],
        ),
        logs=[
            LogLine(step="Install dependencies", level="info",
                    message="Collecting requests==99.99.99"),
            LogLine(step="Install dependencies", level="error",
                    message="ERROR: Could not find a version that satisfies the requirement requests==99.99.99"),
            LogLine(step="Install dependencies", level="error",
                    message="ERROR: No matching distribution found for requests==99.99.99"),
        ],
        diff_hunks=[
            DiffHunk(
                file_path="requirements.txt",
                old_lines=["requests==2.31.0"],
                new_lines=["requests==99.99.99"],
                change_type="modified",
            )
        ],
        raw_payload={},
    )

# Add similar functions for each of the 5 failure classes.
# These let you develop the RCA pipeline before the real repo is producing webhooks.
```

---

## 12. GitHub Ingestor (Full Implementation)

```python
# app/ingestion/github.py
import httpx
import zipfile
import io
from datetime import datetime
from app.config import settings
from app.models.failure import FailureContext, LogLine, CommitInfo, DiffHunk
from app.normalizer.normalizer import normalize_github

class GitHubIngestor:
    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {settings.github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=15,
        )

    async def fetch_context(self, failure_id: str, payload: dict) -> FailureContext:
        run = payload["workflow_run"]
        repo_full = payload["repository"]["full_name"]
        run_id = run["id"]

        logs_text = await self._fetch_logs(repo_full, run_id)
        head_sha = run["head_sha"]
        commit_data = await self._fetch_commit(repo_full, head_sha)
        diff_hunks = self._parse_diff(commit_data)
        log_lines = self._parse_logs(logs_text)

        return normalize_github(
            failure_id=failure_id,
            payload=payload,
            log_lines=log_lines,
            commit_data=commit_data,
            diff_hunks=diff_hunks,
        )

    async def _fetch_logs(self, repo: str, run_id: int) -> str:
        url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/logs"
        r = await self.client.get(url, follow_redirects=True)
        if r.status_code != 200:
            return ""
        # Response is a zip of per-step log files
        try:
            z = zipfile.ZipFile(io.BytesIO(r.content))
            texts = []
            for name in z.namelist():
                with z.open(name) as f:
                    texts.append(f"===== {name} =====\n" + f.read().decode("utf-8", errors="ignore"))
            return "\n".join(texts)
        except zipfile.BadZipFile:
            return r.text

    async def _fetch_commit(self, repo: str, sha: str) -> dict:
        r = await self.client.get(f"https://api.github.com/repos/{repo}/commits/{sha}")
        r.raise_for_status()
        return r.json()

    def _parse_diff(self, commit_data: dict) -> list[DiffHunk]:
        hunks = []
        for f in commit_data.get("files", []):
            patch = f.get("patch", "")
            old_lines = [l[1:] for l in patch.splitlines() if l.startswith("-") and not l.startswith("---")]
            new_lines = [l[1:] for l in patch.splitlines() if l.startswith("+") and not l.startswith("+++")]
            status = f.get("status", "modified")
            change_type = {"added": "added", "removed": "deleted"}.get(status, "modified")
            hunks.append(DiffHunk(
                file_path=f["filename"],
                old_lines=old_lines,
                new_lines=new_lines,
                change_type=change_type,
            ))
        return hunks

    def _parse_logs(self, logs_text: str) -> list[LogLine]:
        lines = []
        current_step = "unknown"
        for raw in logs_text.splitlines():
            if raw.startswith("===== "):
                # Step boundary in zip structure
                current_step = raw.strip("= ").strip()
                continue
            level = "info"
            low = raw.lower()
            if "error" in low or "failed" in low or "failure" in low:
                level = "error"
            elif "warning" in low or "warn" in low:
                level = "warning"
            lines.append(LogLine(step=current_step, level=level, message=raw.strip()))
        # Cap to last 500 lines to keep Claude prompt reasonable
        return lines[-500:]
```

---

## 13. GitLab Stub Ingestor

```python
# app/ingestion/gitlab.py
from app.models.failure import FailureContext

class GitLabIngestor:
    async def fetch_context(self, failure_id: str, payload: dict) -> FailureContext | None:
        # Stub — real integration would mirror GitHub ingestor.
        # Returns None to signal "received but not processed".
        return None
```

---

## 14. Normalizer

```python
# app/normalizer/normalizer.py
from datetime import datetime
from app.models.failure import FailureContext, CommitInfo

def normalize_github(failure_id, payload, log_lines, commit_data, diff_hunks) -> FailureContext:
    run = payload["workflow_run"]
    repo = payload["repository"]
    commit = commit_data["commit"]
    return FailureContext(
        id=failure_id,
        provider="github",
        repo_full_name=repo["full_name"],
        workflow_name=run["name"],
        job_name=run.get("display_title", run["name"]),
        run_id=str(run["id"]),
        run_url=run["html_url"],
        conclusion=run["conclusion"],
        triggered_at=datetime.fromisoformat(run["created_at"].replace("Z", "+00:00")),
        completed_at=datetime.fromisoformat(run["updated_at"].replace("Z", "+00:00")),
        duration_seconds=int(
            (datetime.fromisoformat(run["updated_at"].replace("Z", "+00:00"))
             - datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))).total_seconds()
        ),
        head_commit=CommitInfo(
            sha=commit_data["sha"],
            author=commit["author"]["name"],
            message=commit["message"],
            timestamp=datetime.fromisoformat(commit["author"]["date"].replace("Z", "+00:00")),
            files_changed=[f["filename"] for f in commit_data.get("files", [])],
        ),
        recent_commits=[],
        logs=log_lines,
        diff_hunks=diff_hunks,
        test_results=[],
        raw_payload=payload,
    )
```

---

## 15. Config

```python
# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    anthropic_api_key: str
    github_token: str = ""
    github_webhook_secret: str = ""
    gitlab_webhook_secret: str = ""
    claude_model: str = "claude-sonnet-4-5"
    sqlite_path: str = "/data/pipelineiq.db"
    chroma_path: str = "/data/chroma"
    cors_origins: list[str] = ["http://localhost:5173"]
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
```

---

## 16. Database Initialization

```python
# app/storage/db.py
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import settings
from app.storage.models import Base

engine = create_async_engine(f"sqlite+aiosqlite:///{settings.sqlite_path}", echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@asynccontextmanager
async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
```

---

## 17. Running the Backend Locally

```bash
# Terminal 1: start backend
cd pipelineiq
cp backend/.env.example backend/.env
# Edit backend/.env with real values
docker compose up --build

# Terminal 2: start ngrok
ngrok http 8000

# Terminal 3: test health
curl https://<your-ngrok-subdomain>.ngrok-free.app/health
# Expected: {"status":"ok","version":"0.1.0"}
```

---

**Next Document**: [04_AI_ORCHESTRATION_AND_EVALUATION.md](./04_AI_ORCHESTRATION_AND_EVALUATION.md)
