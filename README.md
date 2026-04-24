# PipelineIQ

**AI-powered Root Cause Analysis (RCA) engine for CI/CD pipelines.**

PipelineIQ sits between your CI/CD provider (GitHub Actions / GitLab CI) and your engineering team. It receives failure webhooks, enriches them with logs, diffs, and commit context, runs a multi-layered anomaly detection pipeline, then calls Anthropic's Claude to produce an actionable RCA report — all in under 15 seconds.

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Backend Framework** | Python 3.11 + FastAPI + Uvicorn | Async HTTP/WebSocket server |
| **Data Schemas** | Pydantic v2 + pydantic-settings | Strict typing, env config, LLM structured output |
| **LLM** | Anthropic Claude Sonnet 4.5 (`anthropic` SDK) | Root-cause reasoning via RAG-enhanced prompts |
| **Relational DB** | SQLAlchemy 2.0 + aiosqlite (SQLite) | Failures, RCA reports, metrics snapshots |
| **Vector DB** | ChromaDB | Failure summary embeddings for similarity retrieval |
| **Graph Analysis** | NetworkX | Correlation graph + betweenness centrality scoring |
| **HTTP Client** | httpx | Async GitHub API calls (logs, commits, diffs) |
| **Frontend** | React 19 + Vite 8 + TailwindCSS v4 | Live dashboard with WebSocket updates |
| **Containerization** | Docker + Docker Compose | One-command backend deployment |
| **Tunnel** | ngrok | Expose local webhook endpoint to GitHub |

---

## Architecture — How It Works

```
GitHub Actions webhook (workflow_run failure)
        │
        ▼
┌─────────────────┐    ┌──────────────┐    ┌──────────────────┐
│  Webhook Router │───▶│  GitHub      │───▶│  Normalizer      │
│  POST /webhook  │    │  Ingestor    │    │  → FailureContext │
│  /github        │    │  (logs,diff) │    │  (unified schema) │
└─────────────────┘    └──────────────┘    └────────┬─────────┘
                                                     │
                                                     ▼
                                        ┌────────────────────────┐
                                        │  Hybrid Anomaly Detect │
                                        │  Layer 1: Rules (regex)│
                                        │  Layer 2: Graph (NX)   │
                                        │  → Candidate[]         │
                                        └───────────┬────────────┘
                                                    │
                                                    ▼
                                        ┌────────────────────────┐
                                        │  LLM Orchestrator      │
                                        │  • RAG: ChromaDB       │
                                        │  • Claude Sonnet 4.5   │
                                        │  → RCAReport (JSON)    │
                                        └───────────┬────────────┘
                                                    │
                              ┌──────────┬──────────┼──────────┐
                              ▼          ▼          ▼          ▼
                          SQLite    ChromaDB    WebSocket    Frontend
                         (persist)  (index)    (broadcast)  (dashboard)
```

---

## Directory Structure

```
Pipeline-IQ/
├── docker-compose.yml          # Backend container orchestration
├── .gitignore
├── README.md
│
├── backend/
│   ├── .env                    # Real secrets (git-ignored)
│   ├── .env.example            # Template to copy
│   ├── Dockerfile
│   ├── pyproject.toml          # Python deps (uv/pip)
│   └── app/
│       ├── main.py             # FastAPI app entry + eval endpoints
│       ├── config.py           # Pydantic Settings (env parsing)
│       ├── models/
│       │   ├── failure.py      # FailureContext, LogLine, DiffHunk, etc.
│       │   ├── rca.py          # RCAReport, Hypothesis, Evidence, Remediation
│       │   └── graph.py        # NodeType, EdgeType enums
│       ├── routers/
│       │   ├── webhooks.py     # POST /webhook/github, /webhook/gitlab
│       │   ├── failures.py     # GET /failures, /failures/{id}
│       │   └── metrics.py      # GET /metrics
│       ├── ingestion/
│       │   ├── github.py       # GitHub API client (logs zip, commits, diffs)
│       │   └── gitlab.py       # GitLab stub
│       ├── normalizer/
│       │   └── normalizer.py   # Provider → FailureContext transform
│       ├── graph/
│       │   ├── builder.py      # NetworkX failure correlation graph
│       │   └── store.py        # GraphStore ABC + in-memory impl
│       ├── detection/
│       │   ├── rules.py        # 12 regex patterns (Layer 1)
│       │   ├── centrality.py   # Betweenness centrality ranker (Layer 2)
│       │   └── hybrid.py       # Rules + graph scoring combined
│       ├── llm/
│       │   ├── client.py       # ClaudeClient (retry, JSON validation)
│       │   ├── prompts.py      # System + user prompt templates
│       │   └── orchestrator.py # End-to-end RCA pipeline
│       ├── storage/
│       │   ├── db.py           # SQLAlchemy async engine + sessions
│       │   ├── models.py       # ORM: FailureRow, RCARow, MetricsSnapshot
│       │   └── vector.py       # ChromaDB persistent vector store
│       ├── ws/
│       │   └── manager.py      # WebSocket connection manager
│       └── evaluation/
│           ├── seed.py         # 5 synthetic failure fixtures
│           └── metrics.py      # Top-1/Top-3 accuracy, MTTD computation
│
└── frontend/
    ├── .env.local              # VITE_API_BASE=http://localhost:8000
    ├── package.json
    ├── vite.config.ts
    ├── index.html
    └── src/
        ├── main.tsx            # React entry
        ├── App.tsx             # SPA router (Feed, Detail, Metrics)
        ├── index.css           # TailwindCSS v4 import
        ├── api/
        │   └── client.ts       # fetch wrappers: listFailures, getFailure, getMetrics
        ├── hooks/
        │   └── useWebSocket.ts # Live WebSocket hook for rca_ready events
        └── pages/
            ├── Feed.tsx        # Failure list with live polling + WS
            ├── FailureDetail.tsx  # Full RCA report view
            └── Metrics.tsx     # Evaluation metrics dashboard
```

---

## Prerequisites

- **Docker Desktop** (with Docker Compose v2)
- **Node.js** ≥ 18 (for the frontend dev server)
- **ngrok** (free account — for exposing webhooks to GitHub)
- An **Anthropic API key** (`sk-ant-...`)
- A **GitHub Personal Access Token** (`ghp_...`) with `repo` scope

---

## Execution Commands — Step by Step

### Step 1: Configure Environment Variables

```bash
# Copy the template
cp backend/.env.example backend/.env

# Edit backend/.env and replace the placeholder values:
#   ANTHROPIC_API_KEY=sk-ant-api03-YOUR_REAL_KEY
#   GITHUB_TOKEN=ghp_YOUR_REAL_TOKEN
#   GITHUB_WEBHOOK_SECRET=your_chosen_secret
```

> **Important:** The `.env` file must NOT have inline comments (no `# comment` after values). Each line should be exactly `KEY=value`.

### Step 2: Start the Backend (Docker)

```bash
# From the project root (Pipeline-IQ/)
docker compose up --build
```

Expected output:
```
✔ Container pipelineiq-backend  Started
pipelineiq-backend  | INFO:  Uvicorn running on http://0.0.0.0:8000
```

Verify it's running:
```bash
curl http://localhost:8000/health
# → {"status":"ok","version":"0.1.0"}
```

### Step 3: Start the Frontend (Vite)

Open a **new terminal**:
```bash
cd frontend
npm install
npm run dev
```

Expected output:
```
VITE v8.0.10  ready in 932 ms
➜  Local:   http://localhost:5173/
```

### Step 4: Open the Dashboard

Open your browser to **http://localhost:5173**

You'll see the PipelineIQ dashboard with three pages:
- **Feed** (`/`) — Live failure list (empty until webhooks arrive or you seed data)
- **Failure Detail** (`/failure/{id}`) — Full RCA report with hypotheses, evidence, remediation
- **Metrics** (`/metrics`) — Top-1/Top-3 accuracy, MTTD

### Step 5: Expose Webhooks with ngrok (Optional — for real GitHub integration)

Open another **new terminal**:
```bash
ngrok http 8000
```

Copy the HTTPS forwarding URL (e.g., `https://xxxx.ngrok-free.app`) and configure it in your GitHub repo:
- **Settings → Webhooks → Add webhook**
- **Payload URL:** `https://xxxx.ngrok-free.app/webhook/github`
- **Content type:** `application/json`
- **Secret:** Same value as `GITHUB_WEBHOOK_SECRET` in `.env`
- **Events:** Select "Workflow runs"

### Step 6: Seed Synthetic Failures (for demo / evaluation)

With the backend running, use these evaluation endpoints:

```bash
# Seed 5 synthetic failures through the full RCA pipeline
curl -X POST http://localhost:8000/eval/seed

# Label ground truth for evaluation
curl -X POST http://localhost:8000/eval/label \
  -H "Content-Type: application/json" \
  -d '{"failure_id":"synth-dep-1","true_class":"dependency_conflict"}'

# Compute accuracy metrics
curl -X POST http://localhost:8000/eval/run
```

---

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Health check |
| `POST` | `/webhook/github` | GitHub webhook receiver |
| `POST` | `/webhook/gitlab` | GitLab webhook receiver (stub) |
| `GET` | `/failures?limit=20` | List recent failures |
| `GET` | `/failures/{id}` | Full failure + RCA detail |
| `GET` | `/failures/{id}/remediation` | Just the remediation |
| `GET` | `/metrics` | Evaluation metrics (Top-1, Top-3, MTTD) |
| `WS` | `/ws/live` | WebSocket for real-time RCA notifications |
| `POST` | `/eval/seed` | Seed 5 synthetic failures |
| `POST` | `/eval/label` | Label a failure with ground truth class |
| `POST` | `/eval/run` | Compute and snapshot evaluation metrics |

---

## Terminal Layout (Recommended)

Run these in **3 separate terminals**:

| Terminal | Command | Purpose |
|----------|---------|---------|
| Terminal 1 | `docker compose up --build` | Backend API (port 8000) |
| Terminal 2 | `cd frontend && npm run dev` | Frontend dashboard (port 5173) |
| Terminal 3 | `ngrok http 8000` | Public webhook URL |
