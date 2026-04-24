# PipelineIQ — System Architecture Document (SAD)

**Document 2 of 4** · Architecture, component design, data flow, tech stack justification

---

## 1. System Context

PipelineIQ sits between your CI/CD provider and your engineering team. It receives failure notifications via webhooks, enriches them with contextual data, runs an AI-powered diagnosis, and delivers an actionable RCA report to a dashboard.

```
          ┌──────────────────────┐
          │  CI/CD Provider      │
          │  (GitHub Actions)    │ ──── webhook ───┐
          │  (GitLab CI stub)    │                 │
          └──────────────────────┘                 │
                                                   ▼
                                          ┌────────────────┐
                                          │  PipelineIQ    │
                                          │  (This system) │
                                          └────────────────┘
                                                   │
         ┌─────────────────────────────────────────┼─────────────────┐
         ▼                                         ▼                 ▼
  ┌──────────────┐                        ┌───────────────┐   ┌────────────┐
  │ Anthropic    │◄──── RCA request ──────│ Backend       │   │ Frontend   │
  │ Claude API   │──── RCA response ────► │ (FastAPI)     │◄─►│ (React)    │
  └──────────────┘                        └───────────────┘   └────────────┘
                                                  │                 ▲
                                                  ▼                 │
                                          ┌───────────────┐         │
                                          │ Storage       │         │
                                          │ SQLite+Chroma │         │
                                          └───────────────┘         │
                                                                    │
                                                              Engineer
                                                              (judge)
```

### External Entities

| Entity | Interaction |
|---|---|
| **GitHub Actions** | Sends webhook on workflow run completion (success/failure) |
| **GitLab CI** | Stub receiver — adapter proves extensibility, no real integration in prototype |
| **Anthropic Claude API** | Receives prompts with failure context, returns structured RCA + remediation |
| **Engineer/Judge** | Views dashboard, triggers failures, reviews RCA reports |

---

## 2. Component Architecture

PipelineIQ is composed of **seven core components** organized into four layers.

```
┌──────────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                          │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  7. React Dashboard (Vite + Tailwind + shadcn/ui)          │  │
│  │     Failure Feed · RCA Detail · Metrics · Similar Failures │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────┬───────────────────────────┘
                                       │ REST + WebSocket
┌──────────────────────────────────────┴───────────────────────────┐
│                         API LAYER                                │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  6. FastAPI Application                                    │  │
│  │     /webhook/*  /failures/*  /metrics  /ws/live            │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────┬───────────────────────────┘
                                       │
┌──────────────────────────────────────┴───────────────────────────┐
│                       PROCESSING LAYER                           │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐              │
│  │1. Ingestion  │ │3. Correlation│ │4. Anomaly    │              │
│  │   Layer      │→│   Graph      │→│   Detection  │              │
│  │              │ │   Builder    │ │   (Hybrid)   │              │
│  └──────────────┘ └──────────────┘ └──────┬───────┘              │
│         ▲                                 │                      │
│         │                                 ▼                      │
│  ┌──────────────┐                  ┌──────────────┐              │
│  │2. Normalizer │                  │5. LLM        │              │
│  │              │                  │   Orchestr.  │──► Claude    │
│  └──────────────┘                  └──────────────┘              │
└──────────────────────────────────────┬───────────────────────────┘
                                       │
┌──────────────────────────────────────┴───────────────────────────┐
│                        STORAGE LAYER                             │
│  ┌────────────────┐  ┌────────────────┐                          │
│  │ SQLite         │  │ ChromaDB       │                          │
│  │ (structured)   │  │ (vector/RAG)   │                          │
│  └────────────────┘  └────────────────┘                          │
└──────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| # | Component | Responsibility | Tech |
|---|---|---|---|
| 1 | **Ingestion Layer** | Receive webhooks, fetch logs/diffs from source APIs | httpx, GitHub SDK |
| 2 | **Normalizer** | Transform provider-specific payloads into unified schema | Pydantic |
| 3 | **Correlation Graph Builder** | Build graph of commits, tests, services, deps | NetworkX |
| 4 | **Anomaly Detection** | Three-layer hybrid: rules + graph centrality + LLM | Python + NetworkX |
| 5 | **LLM Orchestrator** | Compose prompts, call Claude, parse structured output | Anthropic SDK + Pydantic |
| 6 | **FastAPI Application** | HTTP/WS endpoints, request validation, routing | FastAPI, uvicorn |
| 7 | **React Dashboard** | Live failure feed, RCA display, metrics | React, Vite, Tailwind, shadcn/ui |

---

## 3. Data Flow: Failure to RCA (The Critical Path)

This is the most important flow in the system. Understand this completely.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  FAILURE → RCA END-TO-END FLOW                          │
└─────────────────────────────────────────────────────────────────────────┘

 [1] GitHub Actions workflow fails
      │
      ▼
 [2] GitHub sends webhook POST to https://<ngrok>/webhook/github
      │ Payload: workflow_run object, status=completed, conclusion=failure
      ▼
 [3] FastAPI webhook handler validates signature (X-Hub-Signature-256)
      │
      ▼
 [4] Ingestion Layer fetches additional context:
      │   - Full job logs (GitHub API: /actions/runs/{id}/logs)
      │   - Commit diff (GitHub API: /commits/{sha})
      │   - Recent commit history (last 5 commits)
      │   - Test results (if artifact uploaded)
      ▼
 [5] Normalizer transforms all data into FailureContext Pydantic model
      │   {id, timestamp, repo, commit_sha, job_name, logs[], diff, tests[]}
      ▼
 [6] Persist raw FailureContext to SQLite (failures table)
      │
      ▼
 [7] Correlation Graph Builder constructs in-memory NetworkX graph:
      │   Nodes: Commit, File, Test, Dependency, PipelineStep
      │   Edges: MODIFIES, TESTS, DEPENDS_ON, TRIGGERS, FAILS_IN
      ▼
 [8] Anomaly Detection — Three layers in sequence:
      │   [8a] Rule-based scanners find candidate anomalies
      │        (dependency errors, syntax errors, test failures, OOM)
      │   [8b] Graph centrality scores candidates by blast radius
      │        (betweenness centrality on failure subgraph)
      │   [8c] Top 5 candidates passed to Claude with context
      ▼
 [9] LLM Orchestrator composes RCA prompt:
      │   System: role + instructions + output schema
      │   User: failure context + candidates + similar past failures (from Chroma)
      ▼
[10] Claude Sonnet 4.5 generates structured response:
      │   {hypotheses: [{description, confidence, evidence[]}],
      │    remediation: {action, rationale, commands?}}
      ▼
[11] Validate response against Pydantic schema; retry if malformed
      │
      ▼
[12] Persist RCA report to SQLite (rca_reports table)
      │   Write embedding of failure summary to ChromaDB for future retrieval
      ▼
[13] WebSocket broadcast to connected dashboard clients
      │
      ▼
[14] React Dashboard receives event, updates failure feed and detail view
      │
      ▼
[15] Engineer sees RCA on screen in ~15 seconds from step [1]
```

### Timing Budget (Target: <15 seconds total)

| Step | Budget | Notes |
|---|---|---|
| 1–3: Webhook delivery | 2 sec | Network latency |
| 4: Fetch logs + diff | 3 sec | GitHub API calls, parallelize |
| 5–7: Normalize + graph | 1 sec | In-memory, fast |
| 8: Anomaly detection | 1 sec | Rules + graph scoring |
| 9–11: Claude call + validation | 6 sec | LLM latency dominates |
| 12–13: Persist + broadcast | 1 sec | Fast |
| 14–15: Dashboard render | 1 sec | React state update |

---

## 4. Sequence Diagram: Webhook → Dashboard Update

```
GitHub     FastAPI      Ingestion   Graph    Anomaly    Claude    Storage   Dashboard
 Actions   Webhook      Layer       Builder  Detector   Orchestr.           (WebSocket)
   │          │           │           │         │         │          │          │
   │─webhook─►│           │           │         │         │          │          │
   │          │─verify───►│           │         │         │          │          │
   │          │  sig      │           │         │         │          │          │
   │          │           │─fetch────►│         │         │          │          │
   │          │           │  logs/diff│         │         │          │          │
   │          │           │─normalize►│         │         │          │          │
   │          │           │           │         │         │          │          │
   │          │           │──────────►│─build──►│         │          │          │
   │          │           │           │  graph  │         │          │          │
   │          │           │           │         │         │          │          │
   │          │           │           │─detect─►│         │          │          │
   │          │           │           │         │         │          │          │
   │          │           │           │         │─prompt─►│          │          │
   │          │           │           │         │         │─────────►│ (Claude) │
   │          │           │           │         │         │◄─────────│          │
   │          │           │           │         │◄─RCA────│          │          │
   │          │           │           │         │         │          │          │
   │          │           │           │         │─persist────────────►          │
   │          │           │           │         │                    │          │
   │          │◄──────────────────────────────  │                    │          │
   │          │─broadcast─────────────────────────────────────────────────────►│
   │          │                                                                │
   │          │                                                      [visible] │
```

---

## 5. Tech Stack with Justification

| Layer | Choice | Alternatives Considered | Rejection Reason | Production Path |
|---|---|---|---|---|
| **LLM** | Claude Sonnet 4.5 | GPT-4o, Llama 3 | Claude: better reasoning + JSON mode; GPT-4o: slower, pricier; Llama: hosting overhead | Keep Claude; add fallback to secondary provider |
| **LLM orchestration** | Anthropic Python SDK (direct) | LangChain, LlamaIndex | LangChain: 3–4hr debug cost for zero MVP value; direct SDK is cleaner | Stay direct; framework only if complexity demands |
| **Graph DB** | NetworkX in-memory | Neo4j, ArangoDB, NebulaGraph | Neo4j: 4hr Cypher + infra learning; NetworkX has same algorithms | Swap NetworkX → Neo4j via `GraphStore` interface when scale requires |
| **Backend framework** | FastAPI | Flask, Django, Express | FastAPI: Pydantic native, async, auto docs — perfect for this | Keep |
| **Frontend framework** | React + Vite + Tailwind + shadcn/ui | Next.js, Vue, SvelteKit | Vite: instant HMR; shadcn: judge-grade UI in hours | Stay on React; migrate to Next.js when SSR needed |
| **Structured DB** | SQLite | PostgreSQL, MySQL | SQLite: zero setup, sufficient for prototype scale | Swap to Postgres when multi-user |
| **Vector store** | ChromaDB | Pinecone, Weaviate, Qdrant | Chroma: embedded mode, no server, free | Migrate to Qdrant for scale |
| **Anomaly detection** | Hybrid rules + graph + LLM | LSTM time-series, Isolation Forest | LSTM: can't train in 20hrs; hybrid is genuinely stronger for symbolic pipeline data | Add ML layer trained on accumulated failure corpus |
| **Webhooks** | FastAPI direct receivers | n8n, Zapier | External tools add deploy + config burden | Consider n8n when non-engineers need to configure integrations |
| **Containerization** | Docker + docker-compose | Plain venv, Podman | Docker: universal, reproducible | Keep; add Kubernetes for scale |
| **Public URL** | ngrok (free) | Cloudflare tunnel, localtunnel | ngrok: fastest, most reliable free option | Replace with real deployment (Railway, Render, K8s) |

---

## 6. Deployment Topology (Prototype)

```
┌────────────────────── YOUR LAPTOP ──────────────────────┐
│                                                         │
│   ┌─────────────────────────────────────────────────┐   │
│   │        Docker (via docker-compose)              │   │
│   │  ┌─────────────────────┐  ┌──────────────────┐  │   │
│   │  │  FastAPI Backend    │  │  ChromaDB        │  │   │
│   │  │  :8000              │  │  (embedded)      │  │   │
│   │  └─────────┬───────────┘  └──────────────────┘  │   │
│   │            │                                    │   │
│   │  ┌─────────┴───────────┐                        │   │
│   │  │  SQLite file        │                        │   │
│   │  │  (volume mount)     │                        │   │
│   │  └─────────────────────┘                        │   │
│   └─────────────────────────────────────────────────┘   │
│               ▲                        ▲                │
│               │                        │                │
│        ┌──────┴──────┐          ┌──────┴──────┐         │
│        │  ngrok      │          │  Vite dev   │         │
│        │  tunnel     │          │  server     │         │
│        │  :8000 ─► HTTPS│        │  :5173     │         │
│        └──────┬──────┘          └──────┬──────┘         │
│               │                        │                │
└───────────────┼────────────────────────┼────────────────┘
                │                        │
                │ public HTTPS URL       │ deploy to Vercel
                ▼                        ▼
        ┌──────────────┐         ┌──────────────┐
        │ GitHub       │         │ Vercel       │
        │ Webhooks     │         │ (frontend)   │
        │              │         │              │
        │ points to:   │         │ calls:       │
        │ ngrok URL    │         │ ngrok URL    │
        └──────────────┘         └──────────────┘
```

### Environment Variables

Backend expects these in a `.env` file (gitignored):

```bash
# .env.example (commit this, not the real .env)
ANTHROPIC_API_KEY=sk-ant-...
GITHUB_TOKEN=ghp_...              # Personal access token with repo scope
GITHUB_WEBHOOK_SECRET=randomsecret # set this in GitHub webhook config
GITLAB_WEBHOOK_SECRET=randomsecret # for stub
CLAUDE_MODEL=claude-sonnet-4-5
SQLITE_PATH=/data/pipelineiq.db
CHROMA_PATH=/data/chroma
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:5173,https://your-vercel-subdomain.vercel.app
```

---

## 7. Integration Boundaries

### GitHub Adapter (Full Integration)

**Inbound:**
- Webhook `workflow_run` events, `conclusion: failure`
- Signature verified via HMAC-SHA256 with shared secret

**Outbound (to GitHub API):**
- `GET /repos/{owner}/{repo}/actions/runs/{run_id}/logs` — zipped logs
- `GET /repos/{owner}/{repo}/commits/{sha}` — diff, author, message
- `GET /repos/{owner}/{repo}/commits?per_page=5` — recent history

**Auth:** `GITHUB_TOKEN` personal access token.

### GitLab Adapter (Stub)

**Inbound:**
- Accepts GitLab-style webhook payload at `POST /webhook/gitlab`
- Logs receipt to show integration is wired
- Does NOT enrich or process in prototype

**Outbound:** None in prototype.

**UI Signal:** Dashboard shows "GitLab adapter: ready (enable in production)" — proves extensibility without overpromising.

### Jaeger / Prometheus (Mocked)

- Interface definitions exist in code (`TraceStore`, `MetricStore` ABCs)
- Implementations return empty data in prototype
- Document shows where real integrations would plug in

---

## 8. Production-Ready Path (For Judge Credibility)

When a judge asks "how does this scale to production?" — point to this table:

| Prototype Choice | Production Swap | Effort |
|---|---|---|
| NetworkX in-memory | Neo4j graph database | 1–2 days (already have `GraphStore` interface) |
| SQLite | PostgreSQL | 2–3 hours (SQLAlchemy ORM portable) |
| ChromaDB embedded | Qdrant / Pinecone | 1 day |
| ngrok tunnel | Real deployment (Railway, AWS ECS) | 1 day |
| Vite dev server | Vercel static build | 30 min |
| Docker Compose | Kubernetes manifests | 1–2 days |
| GitLab stub | Full GitLab CI integration | 1 day |
| Jaeger mock | Real Jaeger integration | 1–2 days |
| Prometheus mock | Real Prometheus scraping | 1 day |
| Suggest remediation | Human-in-loop execute remediation | 1 week + safety review |
| Claude direct call | Multi-provider LLM router with fallbacks | 2 days |

**Total path to production-grade: ~3 weeks of focused work.** This is defensible and honest.

---

## 9. Non-Functional Requirements

| Requirement | Target (Prototype) | Why |
|---|---|---|
| RCA latency (p95) | < 15 seconds | Hero demo promise |
| RCA latency (p50) | < 10 seconds | Judge impatience |
| Webhook uptime during demo | 100% | ngrok must not disconnect |
| Top-1 RCA accuracy | ≥ 70% on seeded failures | Credibility threshold |
| Top-3 RCA accuracy | ≥ 90% on seeded failures | Forgiveness margin |
| Dashboard load time | < 2 seconds | UX minimum |
| Claude token budget per RCA | < 8000 tokens | Cost control (~$0.04 per RCA) |
| Total Claude spend during hackathon | < $5 | Budget discipline |

---

## 10. Security Posture (Prototype Scope)

**What we DO:**
- Verify GitHub webhook signatures (HMAC-SHA256)
- Store API keys in `.env`, gitignored
- CORS restricted to known frontend origins
- Read-only GitHub token scope

**What we DON'T do (and disclose):**
- No authentication on dashboard (prototype only; judges assume team-internal)
- No multi-tenancy (single repo, single team)
- No audit logging beyond basic request logs
- No encryption at rest (SQLite file in Docker volume)

For production: add OAuth (GitHub SSO), role-based access control, encryption, audit trail.

---

## 11. Folder Structure (Both Repos)

### Main repo (`pipelineiq`)

```
pipelineiq/
├── README.md
├── docker-compose.yml
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── .env.example
│   ├── app/
│   │   ├── main.py                 # FastAPI entry
│   │   ├── config.py               # Settings / env parsing
│   │   ├── models/                 # Pydantic models
│   │   │   ├── failure.py
│   │   │   ├── rca.py
│   │   │   └── graph.py
│   │   ├── routers/                # FastAPI routers
│   │   │   ├── webhooks.py
│   │   │   ├── failures.py
│   │   │   └── metrics.py
│   │   ├── ingestion/              # Component 1
│   │   │   ├── github.py
│   │   │   └── gitlab.py
│   │   ├── normalizer/             # Component 2
│   │   │   └── normalizer.py
│   │   ├── graph/                  # Component 3
│   │   │   ├── builder.py
│   │   │   └── store.py            # GraphStore interface
│   │   ├── detection/              # Component 4
│   │   │   ├── rules.py
│   │   │   ├── centrality.py
│   │   │   └── hybrid.py
│   │   ├── llm/                    # Component 5
│   │   │   ├── client.py
│   │   │   ├── prompts.py
│   │   │   └── orchestrator.py
│   │   ├── storage/                # SQLite + Chroma
│   │   │   ├── db.py
│   │   │   └── vector.py
│   │   ├── ws/                     # WebSocket manager
│   │   │   └── manager.py
│   │   └── evaluation/             # Eval harness
│   │       ├── seed.py
│   │       └── metrics.py
│   └── tests/
├── frontend/                       # Component 7
│   ├── Dockerfile                  # optional
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/                    # HTTP client
│       ├── components/             # shadcn components
│       ├── pages/
│       │   ├── Feed.tsx
│       │   ├── FailureDetail.tsx
│       │   └── Metrics.tsx
│       └── hooks/
│           └── useWebSocket.ts
└── docs/
    ├── 01_SCOPE_AND_EXECUTION_PLAN.md
    ├── 02_SYSTEM_ARCHITECTURE.md
    ├── 03_BACKEND_DESIGN.md
    ├── 04_AI_ORCHESTRATION_AND_EVALUATION.md
    └── 05_STEP_BY_STEP_GUIDE.md
```

### Test app repo (`pipelineiq-testapp`)

```
pipelineiq-testapp/
├── README.md
├── app.py                          # Simple Flask app
├── requirements.txt
├── tests/
│   └── test_app.py
└── .github/
    └── workflows/
        └── ci.yml                  # GitHub Actions workflow
```

---

**Next Document**: [03_BACKEND_DESIGN.md](./03_BACKEND_DESIGN.md)
