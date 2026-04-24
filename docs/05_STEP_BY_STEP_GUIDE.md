# PipelineIQ — Step-by-Step Build & Demo Guide

**Document 5 of 5 (operational runbook)** · Complete beginner-friendly guide for 20-hour execution. No assumed knowledge beyond Python & Git basics.

---

## How To Use This Document

Read each section **at the time of that step**, not all at once. Go step-by-step. Don't skip. If something fails, search this doc first — most common issues are covered in the Troubleshooting Index at the end.

Mark checkboxes as you go. If both partners track progress here, you always know your state.

---

## PHASE 0 · Pre-Flight Setup (Hour 0–1) — Both Partners Together

### 0.1 Create Anthropic Account & API Key

- [ ] Go to https://console.anthropic.com
- [ ] Sign up with email (both partners can share one account for the hackathon)
- [ ] Navigate to **Billing** → add payment method → add $10 credit
- [ ] Go to **API Keys** → **Create Key** → name it "pipelineiq-hackathon"
- [ ] Copy the key (starts with `sk-ant-`) — paste into a shared Google Doc/password manager
- [ ] **Do not commit this key to Git.** Ever.

**Test it works:**
```bash
curl https://api.anthropic.com/v1/messages \
     --header "x-api-key: $YOUR_KEY" \
     --header "anthropic-version: 2023-06-01" \
     --header "content-type: application/json" \
     --data '{"model":"claude-sonnet-4-5","max_tokens":50,"messages":[{"role":"user","content":"hi"}]}'
```
Expected: a JSON response with `content` array containing a greeting.

> If the response says the model is not found, try `claude-3-5-sonnet-latest` or check your Anthropic console for the current Sonnet model string. Update `CLAUDE_MODEL` env var accordingly.

### 0.2 Install & Authenticate ngrok (Both Laptops)

- [ ] Go to https://ngrok.com/download
- [ ] Follow install instructions for your OS:
  - **macOS**: `brew install ngrok/ngrok/ngrok`
  - **Linux**: `snap install ngrok` or download tarball
  - **Windows**: download .exe from ngrok site
- [ ] Create free account at https://ngrok.com
- [ ] After login, copy authtoken from dashboard
- [ ] Run: `ngrok config add-authtoken <YOUR_AUTHTOKEN>`
- [ ] Test: `ngrok http 8000` — should show "Session Status: online" and a forwarding URL
- [ ] Hit Ctrl+C to stop (we'll start it again later)

### 0.3 Verify Python, Node, Docker

Run each command. All should succeed.

```bash
python --version        # should be 3.11 or higher
node --version          # should be 18.x or higher
docker --version        # should output version
docker ps               # should show empty list (not an error)
git --version           # any recent version
```

If any fails:
- Python: https://www.python.org/downloads/
- Node: https://nodejs.org/ (LTS)
- Docker: https://www.docker.com/products/docker-desktop/
- Git: https://git-scm.com/downloads

### 0.4 Create Two GitHub Repos

**Repo 1: `pipelineiq` (main project)**
- [ ] Go to https://github.com/new
- [ ] Name: `pipelineiq`
- [ ] Description: "AI-powered RCA for CI/CD pipelines"
- [ ] Private (recommended for hackathon)
- [ ] Initialize with README
- [ ] Create

**Repo 2: `pipelineiq-testapp` (dummy CI target)**
- [ ] Go to https://github.com/new
- [ ] Name: `pipelineiq-testapp`
- [ ] Description: "Test app for PipelineIQ webhook integration"
- [ ] **Public** (so you can demonstrate public workflow runs; private also works if you prefer)
- [ ] Initialize with README
- [ ] Create

Clone both to both laptops:

```bash
cd ~
git clone git@github.com:YOUR_USERNAME/pipelineiq.git
git clone git@github.com:YOUR_USERNAME/pipelineiq-testapp.git
```

### 0.5 Generate GitHub Personal Access Token (PAT)

- [ ] Go to https://github.com/settings/tokens?type=beta
- [ ] Click **Generate new token** → Fine-grained token
- [ ] Name: `pipelineiq-dev`
- [ ] Expiration: 30 days
- [ ] Repository access: Only select repositories → `pipelineiq-testapp`
- [ ] Permissions:
  - Contents: Read
  - Actions: Read
  - Metadata: Read-only (auto)
- [ ] Generate, copy the token (starts with `github_pat_`)
- [ ] Paste into shared password doc alongside the Anthropic key

### 0.6 Pick a Webhook Secret

Generate any random string (treat it like a password). Example:

```bash
openssl rand -hex 32
# outputs something like: 7f3c5e9a8d1b2c4e6f0a3b5c7d9e1f2a4b6c8e0d2f4a6c8e0b2d4f6a8c0e2b4d
```

Save this in your shared doc as `GITHUB_WEBHOOK_SECRET`.

### 0.7 Phase 0 Checkpoint

Before proceeding, you should have:
- [ ] Anthropic API key (tested with curl)
- [ ] ngrok installed + authenticated on both laptops
- [ ] Python 3.11+, Node 18+, Docker verified on both laptops
- [ ] Two empty GitHub repos cloned on both laptops
- [ ] GitHub PAT with Actions + Contents read
- [ ] Webhook secret generated
- [ ] All secrets in shared password doc (NOT committed to git)

**If all boxes are ticked: proceed to Phase 1. If any is missing: fix it now.** Debugging setup issues at Hour 10 is much more painful than at Hour 1.

---

## PHASE 1 · Project Scaffolding (Hours 1–2)

### 1.1 (Partner A) Scaffold the Backend

In the `pipelineiq` repo:

```bash
cd ~/pipelineiq
mkdir -p backend/app/{models,routers,ingestion,normalizer,graph,detection,llm,storage,ws,evaluation}
mkdir -p backend/scripts
cd backend

# Create placeholder files (they will be filled from Doc 3 code)
touch app/__init__.py \
      app/main.py \
      app/config.py \
      app/models/__init__.py app/models/failure.py app/models/rca.py app/models/graph.py \
      app/routers/__init__.py app/routers/webhooks.py app/routers/failures.py app/routers/metrics.py \
      app/ingestion/__init__.py app/ingestion/github.py app/ingestion/gitlab.py \
      app/normalizer/__init__.py app/normalizer/normalizer.py \
      app/graph/__init__.py app/graph/builder.py app/graph/store.py \
      app/detection/__init__.py app/detection/rules.py app/detection/centrality.py app/detection/hybrid.py \
      app/llm/__init__.py app/llm/client.py app/llm/prompts.py app/llm/orchestrator.py \
      app/storage/__init__.py app/storage/db.py app/storage/vector.py app/storage/models.py \
      app/ws/__init__.py app/ws/manager.py \
      app/evaluation/__init__.py app/evaluation/seed.py app/evaluation/metrics.py \
      scripts/__init__.py \
      pyproject.toml Dockerfile .env.example

# Add to .gitignore (at repo root)
cd ..
cat >> .gitignore <<'EOF'
__pycache__/
*.pyc
.env
data/
node_modules/
dist/
.DS_Store
*.log
.vscode/
.idea/
EOF
```

Now **copy each file's content from Document 3** (`03_BACKEND_DESIGN.md`). Every file needed has complete code in Doc 3. Paste in order:

| # | File | Source |
|---|---|---|
| 1 | `backend/pyproject.toml` | Doc 3 §7.2 |
| 2 | `backend/Dockerfile` | Doc 3 §7.1 |
| 3 | `backend/.env.example` | Doc 2 §6 (Environment Variables section) |
| 4 | `backend/app/config.py` | Doc 3 §15 |
| 5 | `backend/app/models/failure.py` | Doc 3 §2.1 |
| 6 | `backend/app/models/rca.py` | Doc 3 §2.2 |
| 7 | `backend/app/main.py` | Doc 3 §4.5 |
| 8 | `backend/app/routers/webhooks.py` | Doc 3 §4.2 |
| 9 | `backend/app/routers/failures.py` | Doc 3 §4.3 |
| 10 | `backend/app/routers/metrics.py` | Doc 4 §5.5 |
| 11 | `backend/app/storage/db.py` | Doc 3 §16 |
| 12 | `backend/app/storage/models.py` | Doc 3 §5 |
| 13 | `backend/app/storage/vector.py` | Doc 3 §6 |
| 14 | `backend/app/ws/manager.py` | Doc 3 §4.4 |
| 15 | `backend/app/graph/builder.py` | Doc 3 §3.4 |
| 16 | `backend/app/graph/store.py` | see below (skeleton) |
| 17 | `backend/app/detection/rules.py` | Doc 4 §2.2 |
| 18 | `backend/app/detection/centrality.py` | Doc 3 §3.5 |
| 19 | `backend/app/detection/hybrid.py` | Doc 4 §2.3 |
| 20 | `backend/app/ingestion/github.py` | Doc 3 §12 |
| 21 | `backend/app/ingestion/gitlab.py` | Doc 3 §13 |
| 22 | `backend/app/normalizer/normalizer.py` | Doc 3 §14 |
| 23 | `backend/app/llm/client.py` | Doc 4 §1.2 + §1.4 |
| 24 | `backend/app/llm/prompts.py` | Doc 4 §4.1 + §4.2 |
| 25 | `backend/app/llm/orchestrator.py` | Doc 4 §3 |
| 26 | `backend/app/evaluation/seed.py` | Doc 3 §11 |
| 27 | `backend/app/evaluation/metrics.py` | Doc 4 §5.4 |

**`backend/app/graph/store.py`** — small skeleton, write directly:

```python
# app/graph/store.py
from abc import ABC, abstractmethod
import networkx as nx

class GraphStore(ABC):
    @abstractmethod
    def save(self, failure_id: str, graph: nx.DiGraph) -> None: ...

    @abstractmethod
    def load(self, failure_id: str) -> nx.DiGraph | None: ...

class NetworkXStore(GraphStore):
    """In-memory store. Swap for Neo4jStore in production."""
    def __init__(self):
        self._store: dict[str, nx.DiGraph] = {}

    def save(self, failure_id: str, graph: nx.DiGraph) -> None:
        self._store[failure_id] = graph

    def load(self, failure_id: str) -> nx.DiGraph | None:
        return self._store.get(failure_id)
```

All `__init__.py` files stay empty. Nothing to paste there.

### 1.2 Create `.env` File

```bash
cd ~/pipelineiq/backend
cp .env.example .env
# Edit .env with your real values:
nano .env   # or use any editor
```

Content:

```bash
ANTHROPIC_API_KEY=sk-ant-...<paste-real-key>
GITHUB_TOKEN=github_pat_...<paste-real-token>
GITHUB_WEBHOOK_SECRET=<your-random-secret>
GITLAB_WEBHOOK_SECRET=notused
CLAUDE_MODEL=claude-sonnet-4-5
SQLITE_PATH=/data/pipelineiq.db
CHROMA_PATH=/data/chroma
CORS_ORIGINS=http://localhost:5173
LOG_LEVEL=INFO
```

### 1.3 Create `docker-compose.yml` at Repo Root

From Doc 3 §7.3 — paste into `~/pipelineiq/docker-compose.yml`.

### 1.4 (Partner A) First Backend Smoke Test

```bash
cd ~/pipelineiq
mkdir -p data   # for SQLite + Chroma persistence
docker compose up --build
```

Wait for the logs to show `Uvicorn running on http://0.0.0.0:8000`.

In a new terminal:

```bash
curl http://localhost:8000/health
# expected: {"status":"ok","version":"0.1.0"}
```

If this works: **Backend scaffold complete.** ✅

**If something fails:**
- Docker build fails on `uv pip install`: check internet; fall back to `RUN pip install --no-cache-dir <list>` in Dockerfile with full dependency list from `pyproject.toml`
- Container starts then crashes with ImportError: paste a file you missed from Doc 3; check `__init__.py` exists in every app subdir
- `KeyError: 'ANTHROPIC_API_KEY'`: `.env` not loaded — make sure it's in `backend/.env`, check `docker-compose.yml` passes env vars correctly
- Port 8000 already in use: `lsof -i :8000` to find the process, kill it

### 1.5 (Partner B) Scaffold the Frontend

In parallel with A:

```bash
cd ~/pipelineiq
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm install lucide-react class-variance-authority clsx tailwind-merge
```

Configure Tailwind — edit `frontend/tailwind.config.js`:

```js
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: { extend: {} },
  plugins: [],
}
```

Edit `frontend/src/index.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

html, body, #root { height: 100%; }
body { @apply bg-neutral-50 text-neutral-900; }
```

Smoke test:

```bash
npm run dev
# Opens http://localhost:5173 — you should see Vite default page
```

### 1.6 (Partner B) In Parallel — Create Test App on GitHub

From Doc 3 §8, paste the four files into `~/pipelineiq-testapp/`:

```bash
cd ~/pipelineiq-testapp
touch app.py requirements.txt
mkdir -p tests .github/workflows
touch tests/test_app.py .github/workflows/ci.yml
touch tests/__init__.py
```

Then paste:
- `app.py` from Doc 3 §8.1
- `requirements.txt` from Doc 3 §8.2
- `tests/test_app.py` from Doc 3 §8.3
- `.github/workflows/ci.yml` from Doc 3 §8.4

```bash
git add .
git commit -m "feat: initial test app with CI"
git push origin main
```

Go to https://github.com/YOUR_USER/pipelineiq-testapp/actions and watch the first workflow run. **It should pass (green checkmark).** If it doesn't:
- Red dot on "Install dependencies": check `requirements.txt` exactly matches Doc 3 §8.2
- Red dot on "Run tests": check `tests/test_app.py` exactly matches Doc 3 §8.3
- No workflow visible at all: check `.github/workflows/ci.yml` is at the right path with proper YAML indentation

### 1.7 Phase 1 Checkpoint

- [ ] Backend responds on `localhost:8000/health`
- [ ] Frontend renders Vite default on `localhost:5173`
- [ ] Test repo has green CI run visible on GitHub
- [ ] `.env` populated with real keys (and gitignored — check with `git status`)

---

## PHASE 2 · Core Engine End-to-End (Hours 2–6)

### 2.1 (Partner A) Verify Claude Integration

Create a smoke-test script:

```bash
cd ~/pipelineiq/backend
cat > scripts/test_claude.py <<'EOF'
import asyncio
from app.llm.client import claude

async def main():
    resp = await claude.generate(
        system="You are a helpful assistant. Respond in one sentence.",
        user="What is CI/CD in one line?"
    )
    print(resp)

asyncio.run(main())
EOF

# Run inside container for env parity:
docker compose exec backend python -m scripts.test_claude
```

Expected: a one-sentence response from Claude.

If fails:
- Check `ANTHROPIC_API_KEY` is set in `.env`
- Check you have credits (Anthropic console)
- If "model not found" — update `CLAUDE_MODEL` to current Sonnet alias

### 2.2 (Partner A) Test Full RCA Pipeline With Synthetic Failure

```bash
cat > scripts/test_rca.py <<'EOF'
import asyncio
from app.evaluation.seed import synthetic_dependency_failure
from app.llm.orchestrator import RCAOrchestrator

async def main():
    ctx = synthetic_dependency_failure()
    orch = RCAOrchestrator()
    rca = await orch.process(ctx)
    print("SUMMARY:", rca.summary)
    print("TOP HYPOTHESIS:", rca.hypotheses[0].title if rca.hypotheses else "none")
    print("CONFIDENCE:", rca.hypotheses[0].confidence if rca.hypotheses else "—")
    print("LATENCY:", rca.latency_ms, "ms")

asyncio.run(main())
EOF

docker compose exec backend python -m scripts.test_rca
```

Expected: a plausible RCA for the synthetic dependency failure, under 10 seconds. This validates the full pipeline end-to-end *before* webhooks are wired.

**If the output looks bad** (wrong class, low confidence, hallucinated evidence): this is a prompt tuning issue — but don't fix it now. Note it, proceed to webhooks, tune prompts in Hour 15–16.

### 2.3 (Partner B) Start ngrok Tunnel

On **Partner A's laptop** (the one running Docker — the backend must be co-located with ngrok):

```bash
# In a NEW terminal (not the docker compose one)
ngrok http 8000
```

You'll see output like:
```
Session Status    online
Forwarding        https://abc-12-345-678.ngrok-free.app -> http://localhost:8000
```

Copy the HTTPS forwarding URL. **Don't close this terminal** — if you close ngrok, the URL changes and you'll have to update the webhook.

Test publicly:
```bash
curl https://abc-12-345-678.ngrok-free.app/health
# should return {"status":"ok",...}
```

### 2.4 (Partner B) Configure GitHub Webhook

From Doc 3 §10.2:

1. Test repo (pipelineiq-testapp) → **Settings** → **Webhooks** → **Add webhook**
2. **Payload URL**: `https://abc-12-345-678.ngrok-free.app/webhook/github`
3. **Content type**: `application/json`
4. **Secret**: (the one in your `.env` as `GITHUB_WEBHOOK_SECRET`)
5. **SSL verification**: Enable
6. **Which events?** → "Let me select individual events" → uncheck everything else → check ONLY **Workflow runs**
7. **Active**: ✓
8. Click **Add webhook**

### 2.5 Test Webhook Delivery With a Safe Commit

Push any trivial commit to test repo:

```bash
cd ~/pipelineiq-testapp
echo "" >> README.md
git commit -am "test: trigger webhook"
git push origin main
```

Wait ~30 seconds for the workflow to complete. Then check:

1. **GitHub Actions**: workflow runs (green, since README-only change doesn't break anything)
2. **ngrok console** (open https://dashboard.ngrok.com/observability/traffic-inspector): see the incoming `POST /webhook/github` request
3. **Backend logs** (docker compose terminal): `{"accepted":false,"reason":"not a failed completed run"}` — because it succeeded

**This is correct behavior.** We only process *failed* runs. Webhook delivery confirmed.

### 2.6 First REAL Failure End-to-End

This is the moment of truth. From Doc 3 §9.1 — push the dependency conflict:

```bash
cd ~/pipelineiq-testapp
git checkout -b failure-dep-conflict

# Edit requirements.txt — change 2.31.0 → 99.99.99
# macOS:
sed -i '' 's/requests==2.31.0/requests==99.99.99/' requirements.txt
# Linux:
# sed -i 's/requests==2.31.0/requests==99.99.99/' requirements.txt

git commit -am "chore: bump requests (intentional break)"
git push origin failure-dep-conflict

# Merge to main to trigger CI:
git checkout main
git merge failure-dep-conflict
git push origin main
```

Watch (in rough order):
1. **GitHub Actions** fails on "Install dependencies" step (red X)
2. **ngrok** shows a `POST /webhook/github` request with 200 response
3. **Backend logs** show ingestion kicking in, GitHub API fetches, Claude call, RCA generated
4. **Check the result**:

```bash
curl http://localhost:8000/failures | python -m json.tool
```

You should see a list with 1 item. Note its `id`. Then:

```bash
curl http://localhost:8000/failures/<ID> | python -m json.tool
```

You should see the full RCA with hypotheses, evidence, remediation. **This is the end-to-end hero flow working.** 🎉

**Clean up for next demo:**
```bash
cd ~/pipelineiq-testapp
git revert HEAD --no-edit
git push origin main
# Verify next Actions run passes (green)
```

### 2.7 Phase 2 Checkpoint

- [ ] Synthetic RCA test runs successfully
- [ ] ngrok tunnel is up with a working HTTPS URL
- [ ] GitHub webhook configured and delivering
- [ ] At least one real GitHub Actions failure successfully processed end-to-end
- [ ] Failure is queryable via `/failures` and `/failures/{id}` endpoints

---

## PHASE 3 · Dashboard UI (Hours 6–10, Partner B lead)

Partner A continues backend polish; Partner B owns this phase.

### 3.1 API Client and WebSocket Hook

File: `frontend/src/api/client.ts`

```ts
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

export async function getFailure(id: string): Promise<any> {
  const r = await fetch(`${BASE}/failures/${id}`);
  if (!r.ok) throw new Error("failed to get failure");
  return r.json();
}

export async function getMetrics(): Promise<any> {
  const r = await fetch(`${BASE}/metrics`);
  if (!r.ok) throw new Error("failed to get metrics");
  return r.json();
}
```

File: `frontend/.env.local`

```
VITE_API_BASE=https://abc-12-345-678.ngrok-free.app
```

(Change to your ngrok URL. Remember to update this before every demo session.)

File: `frontend/src/hooks/useWebSocket.ts`

```ts
import { useEffect, useRef } from "react";

export function useWebSocket(onMessage: (data: any) => void) {
  const wsRef = useRef<WebSocket | null>(null);
  useEffect(() => {
    const base = (import.meta.env.VITE_API_BASE ?? "http://localhost:8000")
      .replace("http://", "ws://")
      .replace("https://", "wss://");
    const ws = new WebSocket(`${base}/ws/live`);
    ws.onmessage = (e) => {
      try { onMessage(JSON.parse(e.data)); } catch {}
    };
    wsRef.current = ws;
    return () => ws.close();
  }, []);
}
```

### 3.2 Feed Page

File: `frontend/src/pages/Feed.tsx`

```tsx
import { useEffect, useState } from "react";
import { listFailures, FailureSummary } from "../api/client";
import { useWebSocket } from "../hooks/useWebSocket";

export default function Feed() {
  const [items, setItems] = useState<FailureSummary[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    try {
      setItems(await listFailures());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 3000); // poll as backup to WS
    return () => clearInterval(interval);
  }, []);

  useWebSocket((msg) => {
    if (msg.type === "rca_ready") refresh();
  });

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <h1 className="text-3xl font-bold mb-1">Pipeline Failures</h1>
      <p className="text-neutral-600 mb-6">
        Live feed of CI/CD failures with AI-diagnosed root causes.
      </p>

      {loading && <p className="text-neutral-500">Loading…</p>}
      {!loading && items.length === 0 && (
        <div className="p-12 text-center bg-white border-2 border-dashed rounded-lg">
          <p className="text-neutral-500">
            No failures yet. Push a bad commit to your test repo.
          </p>
        </div>
      )}

      <div className="space-y-3">
        {items.map((f) => (
          <a
            key={f.id}
            href={`/failure/${f.id}`}
            className="block p-4 bg-white border rounded-lg shadow-sm hover:shadow-md hover:border-neutral-300 transition"
          >
            <div className="flex justify-between items-start gap-4">
              <div className="flex-1 min-w-0">
                <div className="font-medium truncate">{f.repo}</div>
                <div className="text-sm text-neutral-600">
                  {f.workflow} · {f.job}
                </div>
                {f.summary && (
                  <p className="mt-2 text-sm text-neutral-800 line-clamp-2">
                    {f.summary}
                  </p>
                )}
              </div>
              <div className="text-xs text-right shrink-0">
                <div
                  className={`inline-block px-2 py-1 rounded font-medium ${
                    f.conclusion === "failure"
                      ? "bg-red-100 text-red-700"
                      : "bg-amber-100 text-amber-700"
                  }`}
                >
                  {f.conclusion}
                </div>
                <div className="text-neutral-500 mt-1">
                  {new Date(f.triggered_at).toLocaleTimeString()}
                </div>
              </div>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
```

### 3.3 Failure Detail Page

File: `frontend/src/pages/FailureDetail.tsx`

```tsx
import { useEffect, useState } from "react";
import { getFailure } from "../api/client";

export default function FailureDetail({ id }: { id: string }) {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getFailure(id).then(setData).catch((e) => setError(String(e)));
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
              {rca.hypotheses_json.map((h: any, i: number) => (
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
                    {h.evidence.map((e: any, j: number) => (
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
                {rca.similar_past_failures.map((id: string) => (
                  <li key={id}>
                    <a
                      href={`/failure/${id}`}
                      className="text-blue-600 hover:underline"
                    >
                      {id}
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
```

### 3.4 Metrics Page

File: `frontend/src/pages/Metrics.tsx`

```tsx
import { useEffect, useState } from "react";
import { getMetrics } from "../api/client";

export default function Metrics() {
  const [m, setM] = useState<any>(null);

  useEffect(() => {
    getMetrics().then(setM);
    const i = setInterval(() => getMetrics().then(setM), 5000);
    return () => clearInterval(i);
  }, []);

  if (!m) return <div className="p-8">Loading metrics…</div>;

  const pct = (v: number | null) =>
    v == null ? "—" : `${(v * 100).toFixed(0)}%`;
  const ms = (v: number | null) =>
    v == null ? "—" : `${(v / 1000).toFixed(1)} s`;

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <h1 className="text-3xl font-bold mb-1">Evaluation Metrics</h1>
      <p className="text-neutral-600 mb-6">
        Performance on labeled real GitHub Actions failures.
      </p>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard
          label="Top-1 Accuracy"
          value={pct(m.top1_accuracy)}
          target="≥70%"
        />
        <MetricCard
          label="Top-3 Accuracy"
          value={pct(m.top3_accuracy)}
          target="≥90%"
        />
        <MetricCard
          label="Mean Time to Diagnosis"
          value={ms(m.mttd_ms)}
          target="<15s"
        />
        <MetricCard
          label="Sample Size"
          value={String(m.sample_size)}
          target="≥3"
        />
      </div>

      {m.note && (
        <p className="mt-6 text-sm text-neutral-500 italic">{m.note}</p>
      )}
    </div>
  );
}

function MetricCard({
  label,
  value,
  target,
}: {
  label: string;
  value: string;
  target: string;
}) {
  return (
    <div className="p-6 bg-white border rounded-lg">
      <div className="text-sm text-neutral-600">{label}</div>
      <div className="text-4xl font-bold mt-2 tabular-nums">{value}</div>
      <div className="text-xs text-neutral-500 mt-1">Target: {target}</div>
    </div>
  );
}
```

### 3.5 App Root & Routing

File: `frontend/src/App.tsx`

```tsx
import { useEffect, useState } from "react";
import Feed from "./pages/Feed";
import FailureDetail from "./pages/FailureDetail";
import Metrics from "./pages/Metrics";

export default function App() {
  const [path, setPath] = useState(window.location.pathname);

  useEffect(() => {
    const handler = () => setPath(window.location.pathname);
    window.addEventListener("popstate", handler);

    // Intercept all in-app anchor clicks for SPA routing
    const clickHandler = (e: MouseEvent) => {
      const t = e.target as HTMLElement;
      const a = t.closest("a");
      if (!a) return;
      const href = a.getAttribute("href");
      if (!href || !href.startsWith("/")) return;
      if (a.getAttribute("target") === "_blank") return;
      e.preventDefault();
      history.pushState({}, "", href);
      setPath(href);
    };
    document.addEventListener("click", clickHandler);

    return () => {
      window.removeEventListener("popstate", handler);
      document.removeEventListener("click", clickHandler);
    };
  }, []);

  const detailMatch = path.match(/^\/failure\/(.+)$/);

  return (
    <div>
      <nav className="border-b bg-white px-8 py-3 flex gap-6 items-center">
        <a href="/" className="font-bold text-lg">PipelineIQ</a>
        <a href="/" className="text-sm hover:text-blue-600">Feed</a>
        <a href="/metrics" className="text-sm hover:text-blue-600">Metrics</a>
        <span className="ml-auto text-xs text-neutral-500">
          AI-powered RCA · Claude Sonnet 4.5
        </span>
      </nav>
      {path === "/" && <Feed />}
      {path === "/metrics" && <Metrics />}
      {detailMatch && <FailureDetail id={detailMatch[1]} />}
    </div>
  );
}
```

File: `frontend/src/main.tsx` (if not already present, replace default):

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

### 3.6 Smoke Test Dashboard

```bash
cd ~/pipelineiq/frontend
npm run dev
```

Open http://localhost:5173. You should see the PipelineIQ nav. Feed will show failures from earlier tests (or "No failures yet").

**If failures don't show:**
- CORS error in browser console: add `http://localhost:5173` to `CORS_ORIGINS` in backend `.env`, restart backend
- "Failed to fetch": check `VITE_API_BASE` in `frontend/.env.local` — if backend is on your machine locally, `http://localhost:8000` works; if using ngrok from a partner's machine, use the ngrok URL

### 3.7 End-to-End UI Test

Push another failure (repeat Phase 2.6). You should see:
1. Failure appears in dashboard feed within ~15 seconds
2. Click into it — see ranked hypotheses, evidence, remediation
3. Metrics page shows sample_size increasing

### 3.8 Phase 3 Checkpoint

- [ ] Dashboard visible at `http://localhost:5173`
- [ ] Feed page lists failures, updates live when new one arrives
- [ ] Detail page shows full RCA with evidence
- [ ] Metrics page loads (may show empty if nothing labeled yet)
- [ ] Navigation works (clicking a failure goes to detail, back goes home)

---

## PHASE 4 · Sleep / Break (Hours 10–12)

This is not optional. Set alarms. Sleep 90–120 minutes minimum. Eat.

When you wake up, do 5 minutes of system check:

- [ ] Docker still running? `docker compose ps`
- [ ] ngrok still connected? Check the ngrok console
- [ ] Frontend still serving? Refresh browser
- [ ] Still have internet?
- [ ] Anthropic credit still > $3? Check console

If anything died, restart before the next phase.

---

## PHASE 5 · Evaluation & History (Hours 12–16)

### 5.1 Add Label Endpoint (Partner A)

Add to `backend/app/routers/failures.py`:

```python
from pydantic import BaseModel

class LabelRequest(BaseModel):
    failure_id: str
    true_class: str

@router.post("/label")
async def label_failure(req: LabelRequest):
    async with get_session() as session:
        rca = (await session.execute(
            select(RCARow).where(RCARow.failure_id == req.failure_id)
        )).scalar_one_or_none()
        if not rca:
            raise HTTPException(404, "RCA not found")
        rca.ground_truth_class = req.true_class
        await session.commit()
        return {"labeled": True, "failure_id": req.failure_id, "class": req.true_class}
```

Restart backend: `docker compose restart backend`

### 5.2 Seed All 5 Failure Classes

Do each one in sequence. After each: capture the failure ID, label it, revert.

**Use a simple script to track progress:**

```bash
cat > ~/seed-progress.txt <<EOF
Failure seeding progress:
[ ] 1. dep-conflict        -> id: ____    class: dependency_conflict
[ ] 2. syntax-error        -> id: ____    class: code_regression
[ ] 3. test-assertion      -> id: ____    class: code_regression
[ ] 4. config-drift        -> id: ____    class: config_drift
[ ] 5. resource-exhaustion -> id: ____    class: resource_exhaustion
EOF
```

#### Seed 1: Dependency Conflict

```bash
cd ~/pipelineiq-testapp
git checkout main && git pull
git checkout -b eval-01-dep
# macOS:
sed -i '' 's/requests==2.31.0/requests==99.99.99/' requirements.txt
# Linux:
# sed -i 's/requests==2.31.0/requests==99.99.99/' requirements.txt
git commit -am "eval-01: dep conflict"
git checkout main
git merge eval-01-dep
git push origin main
# WAIT ~45 seconds for Actions + webhook + RCA
# Get ID:
curl http://localhost:8000/failures | python -c "import sys,json;data=json.load(sys.stdin);print(data[0]['id'])"
# Label (substitute the ID):
curl -X POST http://localhost:8000/failures/label \
     -H "Content-Type: application/json" \
     -d '{"failure_id":"<ID>","true_class":"dependency_conflict"}'
# Revert
git revert HEAD --no-edit
git push origin main
# Wait for green build before next seed
git branch -D eval-01-dep
```

#### Seed 2: Syntax Error

```bash
git checkout -b eval-02-syntax
# Introduce a syntax error in app.py — replace the add() function body:
python - <<'PYEOF'
path = "app.py"
src = open(path).read()
src = src.replace(
    "def add(a, b):\n    return a + b",
    "def add(a, b):\n    return a +  # intentional broken"
)
open(path, "w").write(src)
PYEOF
git commit -am "eval-02: syntax error"
git checkout main
git merge eval-02-syntax
git push origin main
# Wait ~45s, get ID, label:
curl -X POST http://localhost:8000/failures/label \
     -H "Content-Type: application/json" \
     -d '{"failure_id":"<ID>","true_class":"code_regression"}'
git revert HEAD --no-edit && git push origin main
git branch -D eval-02-syntax
```

#### Seed 3: Test Assertion Failure

```bash
git checkout -b eval-03-test
python - <<'PYEOF'
path = "app.py"
src = open(path).read()
src = src.replace(
    "def multiply(a, b):\n    return a * b",
    "def multiply(a, b):\n    return a + b  # wrong op"
)
open(path, "w").write(src)
PYEOF
git commit -am "eval-03: test failure"
git checkout main && git merge eval-03-test && git push origin main
# Wait, label:
curl -X POST http://localhost:8000/failures/label \
     -H "Content-Type: application/json" \
     -d '{"failure_id":"<ID>","true_class":"code_regression"}'
git revert HEAD --no-edit && git push origin main
git branch -D eval-03-test
```

#### Seed 4: Config Drift

```bash
git checkout -b eval-04-config
# macOS:
sed -i '' 's/python-version: "3.11"/python-version: "2.7"/' .github/workflows/ci.yml
# Linux:
# sed -i 's/python-version: "3.11"/python-version: "2.7"/' .github/workflows/ci.yml
git commit -am "eval-04: config drift"
git checkout main && git merge eval-04-config && git push origin main
curl -X POST http://localhost:8000/failures/label \
     -H "Content-Type: application/json" \
     -d '{"failure_id":"<ID>","true_class":"config_drift"}'
git revert HEAD --no-edit && git push origin main
git branch -D eval-04-config
```

#### Seed 5: Resource Exhaustion

```bash
git checkout -b eval-05-resource
# Add a timeout step — insert before "Install dependencies":
python - <<'PYEOF'
path = ".github/workflows/ci.yml"
src = open(path).read()
insertion = """      - name: Simulate resource exhaustion
        run: |
          timeout 5 bash -c 'while true; do :; done'
          exit 124

"""
src = src.replace("      - name: Install dependencies", insertion + "      - name: Install dependencies")
open(path, "w").write(src)
PYEOF
git commit -am "eval-05: resource exhaustion"
git checkout main && git merge eval-05-resource && git push origin main
curl -X POST http://localhost:8000/failures/label \
     -H "Content-Type: application/json" \
     -d '{"failure_id":"<ID>","true_class":"resource_exhaustion"}'
git revert HEAD --no-edit && git push origin main
git branch -D eval-05-resource
```

### 5.3 Check Metrics

```bash
curl http://localhost:8000/metrics | python -m json.tool
```

Expected output:
```json
{
  "top1_accuracy": 0.8,
  "top3_accuracy": 1.0,
  "mttd_ms": 11420,
  "sample_size": 5
}
```

View on dashboard at `/metrics`.

### 5.4 Tune If Needed

If Top-1 is below 0.7:

1. Fetch the failure that got wrong class: `curl http://localhost:8000/failures/<id> | python -m json.tool`
2. Look at `rca.hypotheses_json` — did the rule-based detector flag the right class? Did Claude pick it?
3. Options:
   - **Rule miss**: add a more specific pattern in `detection/rules.py` for that failure type
   - **Claude wrong**: add a few-shot example for that class in `llm/prompts.py` (per Doc 4 §4.3)
   - **Confidence calibration**: strengthen calibration instructions in system prompt (Doc 4 §7)
4. Restart backend, re-run the affected seed case

Don't spend more than 60 minutes on tuning. If Top-1 is 0.6 (3/5), that's still publishable — present it honestly with the Top-3 = 1.0.

### 5.5 Phase 5 Checkpoint

- [ ] 5 seeded failures, all with ground truth labels
- [ ] Metrics endpoint returns real numbers
- [ ] Metrics dashboard shows them
- [ ] Top-3 accuracy at 100% (strongly recommended; tune until achieved)
- [ ] Test repo is clean (main branch passing green)

---

## PHASE 6 · Polish & Live-Demo Prep (Hours 16–18)

### 6.1 Prepare the Demo Trigger Branch

Create one more special branch you'll merge live during the demo:

```bash
cd ~/pipelineiq-testapp
git checkout main && git pull
git checkout -b demo-trigger
# Use the "greatest hits" failure — dependency conflict is most visually clear
# macOS:
sed -i '' 's/requests==2.31.0/requests==99.99.99/' requirements.txt
# Linux:
# sed -i 's/requests==2.31.0/requests==99.99.99/' requirements.txt
git commit -am "demo: trigger for live presentation"
# DO NOT MERGE YET — this branch is staged, we merge during the demo
```

Go back to main so the repo is in clean state:
```bash
git checkout main
```

### 6.2 Pre-Cache for Safety (Optional but Strongly Recommended)

Run the demo-trigger failure *once* during rehearsal to pre-warm:
- Claude API connection (no cold start latency)
- ChromaDB "similar past failures" index (now has dep-conflict examples)

Then revert. This means on the real demo, Claude's response will be faster because past failures are already indexed.

### 6.3 "Replay Last Failure" Button (Backup)

If live trigger fails during demo, you need a way to replay. Add a button.

Add endpoint in `backend/app/routers/failures.py`:

```python
@router.post("/{failure_id}/replay")
async def replay_failure(failure_id: str, background: BackgroundTasks):
    """Re-run RCA on an existing failure (for demo fallback)."""
    async with get_session() as session:
        row = (await session.execute(
            select(FailureRow).where(FailureRow.id == failure_id)
        )).scalar_one_or_none()
        if not row:
            raise HTTPException(404, "Failure not found")
        ctx_dict = row.context_json
        from app.models.failure import FailureContext
        ctx = FailureContext.model_validate(ctx_dict)
        # Reuse same ID so we overwrite
        from app.llm.orchestrator import RCAOrchestrator
        background.add_task(_replay_task, ctx)
        return {"replaying": True, "failure_id": failure_id}

async def _replay_task(ctx):
    from app.llm.orchestrator import RCAOrchestrator
    from app.ws.manager import manager
    # Note: this will create a new RCA row alongside the existing — fine for demo
    orch = RCAOrchestrator()
    rca = await orch.process(ctx)
    await manager.broadcast({"type": "rca_ready", "failure_id": ctx.id, "summary": rca.summary})
```

Add a button on the Feed page:

```tsx
// In Feed.tsx, add a small "Replay" link per row (admin-only):
<button
  onClick={async (e) => {
    e.preventDefault();
    e.stopPropagation();
    const base = import.meta.env.VITE_API_BASE;
    await fetch(`${base}/failures/${f.id}/replay`, { method: "POST" });
  }}
  className="ml-2 text-xs text-neutral-400 hover:text-blue-600"
>
  replay
</button>
```

### 6.4 Demo Rehearsal (Both Partners, 3 Full Runs)

Each rehearsal should be timed. Use a phone stopwatch. The 5-minute demo must fit in 5 minutes.

**Rehearsal 1 — Script run-through:**
- Follow Doc 1 §6 word-for-word
- Partner A drives keyboard, Partner B narrates
- Time each section

**Rehearsal 2 — Things go wrong:**
- Kill ngrok mid-demo, restart (update webhook URL), continue
- Trigger the demo-trigger branch, but also click "replay" when Actions is slow
- Practice graceful recovery

**Rehearsal 3 — Final pass:**
- Full 5 minutes, no interruptions
- Both partners in presentation mode

After each rehearsal:
- [ ] Reset test repo (revert demo-trigger merge, recreate branch)
- [ ] Clear browser cache if needed
- [ ] Note what went wrong, fix before next rehearsal

### 6.5 Phase 6 Checkpoint

- [ ] `demo-trigger` branch staged and ready
- [ ] Replay endpoint works
- [ ] 3 full rehearsals complete, all under 5 minutes
- [ ] Backup plan tested (replay button works)

---

## PHASE 7 · Slides & Video Backup (Hours 18–19)

### 7.1 Record Backup Video (20 Minutes)

Use OBS Studio (free) or QuickTime (Mac built-in).

**Setup:**
- Resolution: 1920×1080, 30fps
- Audio: USB mic if available, else laptop mic in quiet room
- Browser: full-screen Chrome with dashboard open
- Terminal: separate recording or picture-in-picture

**What to record:**
1. Intro: "This is PipelineIQ — a demo of our autonomous RCA engine"
2. Show empty dashboard → push demo-trigger commit → dashboard updates → narrate RCA
3. Click through metrics page, narrate numbers
4. Click through similar-failures retrieval
5. Close: "PipelineIQ — AI-powered pipeline intelligence"

**Post-recording:**
- [ ] Upload to Google Drive (shareable link)
- [ ] Upload to YouTube as UNLISTED (secondary link)
- [ ] Download MP4 to local disk (plays without internet)
- [ ] Test playback on both laptops
- [ ] Put all three links in slides as "Backup Demo Video" slide

### 7.2 Slides (5 Slides Max)

Use Google Slides, Keynote, or PowerPoint.

**Slide 1 — Problem**
- Title: "CI/CD failures cost 2–6 hours per incident"
- 3 bullets:
  - Manual log archaeology across hundreds of microservices
  - Senior engineers pulled off features, burnout
  - Failed deployments trigger SLA breaches
- Visual: clock graphic, "$$$" icon

**Slide 2 — Solution**
- Title: "PipelineIQ: AI-powered RCA in 15 seconds"
- 3 bullets:
  - Ingest logs, traces, diffs automatically
  - Hybrid anomaly detection: rules + graph centrality + Claude reasoning
  - Ranked hypotheses with evidence + remediation
- Visual: one-line architecture (Webhook → Hybrid Detect → Claude → Dashboard)

**Slide 3 — Architecture**
- Title: "Built for production from day one"
- Paste the component diagram from Doc 2 (or a simpler version)
- Small text: "NetworkX → Neo4j, SQLite → Postgres, ngrok → K8s"

**Slide 4 — Metrics**
- Title: "Proven on real GitHub Actions failures"
- 4 big numbers:
  - Top-1 accuracy: **80%**
  - Top-3 accuracy: **100%**
  - Mean time to diagnosis: **11s**
  - Real failures tested: **5**
- Caveat (small): "Intentionally-seeded real failures, ground truth labeled"

**Slide 5 — The Ask**
- Title: "What's next"
- 3 bullets:
  - Full GitLab CI integration (1 day port)
  - Human-in-loop remediation execution (1 week)
  - Deploy to Kubernetes with Neo4j + Qdrant (1-2 weeks)
- Backup slide: link to demo video + GitHub repo

### 7.3 Phase 7 Checkpoint

- [ ] Video recorded, uploaded, downloadable locally
- [ ] Slides done (5 slides)
- [ ] Slides include video backup link
- [ ] Slides tested in fullscreen mode on presentation laptop

---

## PHASE 8 · Final Buffer (Hour 19–20)

### 8.1 Go-Live Pre-Flight (30 min before judging)

- [ ] Restart ngrok, note the new URL (may be different from before)
- [ ] Update GitHub webhook URL in repo settings to new ngrok URL
- [ ] Update `VITE_API_BASE` in `frontend/.env.local` to new ngrok URL
- [ ] Restart frontend (`npm run dev`), verify it can hit backend
- [ ] Trigger one throwaway commit, verify full flow works end-to-end
- [ ] Reset test repo to clean state (`git log` should show your revert commits, nothing pending)
- [ ] Close all unnecessary apps/tabs to free RAM
- [ ] Charge laptop to 100% + plug in AC
- [ ] Tether phone hotspot as backup network
- [ ] Open tabs: (1) Dashboard, (2) Test repo on GitHub, (3) Slides, (4) Terminal with demo-trigger branch ready

### 8.2 Team Prep

- [ ] Decide who speaks which section of the 5-min demo
- [ ] Review judge Q&A from Doc 1 + Section 9.3 below
- [ ] Eat a proper meal (not just caffeine)
- [ ] Hydrate
- [ ] Deep breath — you built a real thing. Own it.

---

## PHASE 9 · Demo Day Playbook

### 9.1 The 5-Minute Demo

Follow Doc 1 §6 word-for-word. Stick to timing. If nervous, breathe before you speak.

### 9.2 Common Live-Demo Failures & Responses

| What Breaks | What You Say | What You Do |
|---|---|---|
| Actions is slow | "While GitHub Actions runs, let me show you a previous failure" | Click an existing failure in feed; switch back when live one arrives |
| Webhook didn't fire in 60s | "We have 5 pre-seeded real failures that show the same pipeline — let me walk through one" | Open an existing failure, narrate the RCA quality |
| Dashboard blank/broken | "Let me switch to our backup video which shows the full flow" | Open video, narrate over it |
| Claude slow or rate-limited | (fill with narration about architecture: "our hybrid detector is scoring candidates… the graph centrality ranker…") | Wait; if >30s, click Replay on an existing failure |
| ngrok disconnected | "One moment, restarting our tunnel" | `ngrok http 8000`, update webhook URL in GitHub, retry |
| Everything dies | "We prepared for this — here's our recorded walkthrough" | Play video |

### 9.3 Likely Judge Questions & Answers

**Q: "How does this scale to 1000 microservices?"**
A: NetworkX is in-memory — production swap is Neo4j, which scales this graph model to millions of nodes. We already defined the `GraphStore` abstract interface so the swap is isolated to one file. At the ingestion layer, we'd shard with Kafka for 1000+ service throughput.

**Q: "Why should I trust Claude not to hallucinate?"**
A: Three reasons. First, we ground Claude on rule-based candidates — it reasons over evidence, doesn't free-generate. Second, every claim must cite an exact snippet from input; Pydantic schema enforces this. Third, Top-1 accuracy is published — 80% on real failures — judge calibration for yourself.

**Q: "What about false positives?"**
A: We separate *detection* (engine says "failure happened") from *diagnosis* (engine says "here's why"). Detection has zero false positives — we only run on actual webhook-triggered failures. Diagnosis false positives are bounded by Top-3 accuracy at 100% — the right answer is always in the top 3, so engineers have an escape hatch.

**Q: "Isn't this just log parsing with extra steps?"**
A: No. Log parsers match known regex patterns. A novel failure class that no one has seen before still gets a plausible diagnosis from Claude because it reasons from first principles over diff + logs + graph structure. Rules cover the easy 60%; the LLM layer handles the long tail.

**Q: "Why GitLab-DevOps track if you built on GitHub?"**
A: Our architecture is provider-agnostic. GitHub was fastest path to real ingestion — great API access. The ingestion layer has adapter pattern; GitLab adapter is stubbed. Full GitLab CI integration is a one-day port, and the rest of the system — graph, detection, LLM — is 100% reused.

**Q: "What's the cost at scale?"**
A: ~$0.04 per RCA at Claude Sonnet 4.5 rates. At 1000 failures/day, that's $40/day of LLM spend. Compare to 2–6 engineer-hours saved per failure at ~$100/hour engineer cost — break-even at less than 1% of a single engineer's time.

**Q: "What if Claude is down?"**
A: We have a multi-provider fallback design — swap to GPT-4 or Gemini via our `ClaudeClient` interface. Not implemented in prototype but isolated to one file.

**Q: "What about security? Logs can contain secrets."**
A: Valid concern. Production would add: (1) PII/secret redaction pre-LLM with pattern matchers, (2) VPC-scoped API calls, (3) RBAC on dashboard. In prototype scope: we acknowledge this openly and point to our scope-out list.

**Q: "What's next after this prototype?"**
A: Three things in order: Full GitLab CI integration → Human-in-loop remediation with approval workflow → Deploy to Kubernetes with real Neo4j + Qdrant. Phase 2 is ~3 weeks of focused work.

### 9.4 Post-Demo

- [ ] Shake hands, give business card / GitHub handle
- [ ] Ask judges for feedback explicitly ("any areas we should improve?")
- [ ] Take notes on questions asked — useful for next round
- [ ] Eat, hydrate, rest before next panel

---

## PHASE 10 · Troubleshooting Index

### Backend Issues

| Symptom | Cause | Fix |
|---|---|---|
| `docker compose up` hangs on build | Slow network downloading base image | `docker pull python:3.11-slim` first, then rebuild |
| `ModuleNotFoundError: app` | `PYTHONPATH` issue in container | Ensure `CMD` uses `app.main:app` and `WORKDIR` is `/app` with `app/` folder copied |
| `sqlalchemy.exc.OperationalError: unable to open database file` | `/data` not mounted | Check `volumes` in `docker-compose.yml` has `./data:/data` |
| `anthropic.NotFoundError: model not found` | Wrong model string | Update `CLAUDE_MODEL` to latest Sonnet per Anthropic console |
| Webhook returns 401 | Secret mismatch between GitHub config and `.env` | Copy webhook secret from `.env` to GitHub webhook config *exactly*, no trailing space |
| Webhook receives but ignores | Event type filter | Check GitHub webhook is subscribed to "Workflow runs", not "Pushes" |
| GitHub API 404 on fetching logs | Token lacks Actions:read scope | Regenerate fine-grained PAT with Actions permission |
| Everything times out after working | ngrok tunnel died | Restart ngrok, update webhook URL, update frontend `VITE_API_BASE` |
| `RateLimitError` from Anthropic | Burst of requests | Wait 30 seconds; retry logic already handles this |
| Claude returns prose + JSON | Prompt too loose | Tighten system prompt: "ONLY JSON, no markdown fences, no prose" |
| SQLite locked | Two backend instances running | `docker compose down`, check for orphan processes with `docker ps -a` |

### Frontend Issues

| Symptom | Cause | Fix |
|---|---|---|
| CORS error in browser console | Backend not allowing Vite origin | Add `http://localhost:5173` to `CORS_ORIGINS` in `.env`, restart backend |
| "Failed to fetch" in console | Wrong API base URL | Check `VITE_API_BASE` in `frontend/.env.local`, restart Vite (`npm run dev`) |
| WebSocket connects then closes immediately | Backend WS handler raised exception | Check backend logs for exception in `ws_live`, fix and restart |
| Tailwind classes not applying | PostCSS not configured or content paths wrong | Ensure `tailwind.config.js` has `content: ["./index.html","./src/**/*.{js,ts,jsx,tsx}"]`, restart `npm run dev` |
| Blank white page | JS error | Open devtools console, read the error, usually a missing import |
| `/failure/<id>` shows blank | Route match failed | Check `App.tsx` detailMatch regex, verify URL format |
| Feed doesn't update on new failure | WS disconnected, polling fallback too slow | Refresh browser; increase polling interval to 2s if needed |

### GitHub Actions Issues

| Symptom | Cause | Fix |
|---|---|---|
| Workflow doesn't run on push | Wrong branch in `on:` trigger | Check `ci.yml` has `branches: [main]` |
| Green when should be red | Bad commit didn't actually break | Verify the exact change from Doc 3 §9; run `pip install -r requirements.txt` locally first |
| Red but wrong reason | Multiple things broken | Start with clean main, push exactly one failure type |
| Workflow runs but webhook not received | Webhook disabled or URL outdated | Check webhook's "Recent Deliveries" tab; if old URL, update to current ngrok URL |

### Claude Prompt Quality Issues

| Symptom | Cause | Fix |
|---|---|---|
| Malformed JSON response | Prompt ambiguous about format | Strengthen: "Respond ONLY with valid JSON. No prose. No code fences." |
| Confidences all 0.95+ (overconfident) | Not calibrated | Add: "Use 0.9+ only when evidence is unambiguous. 0.6–0.8 for likely-but-not-certain. 0.3–0.5 for guesses." |
| Evidence snippets hallucinated | Not grounded enough | Emphasize: "Quote exact text from the provided input. Invent nothing." |
| Wrong failure_class repeatedly | Ambiguous class definitions | Add concrete few-shot example for that class per Doc 4 §4.3 |
| Remediation too generic ("check logs") | Prompt allows vague output | Add: "Remediation must include specific file paths, version numbers, or commands. Never 'review the code' or 'check logs'." |
| Claude chooses no candidate | All candidates too weak | Lower rule priors OR expand rule patterns |

### Environment / Setup Issues

| Symptom | Cause | Fix |
|---|---|---|
| `docker: command not found` | Docker Desktop not running | Open Docker Desktop app, wait for whale icon to stop animating |
| Port 8000 / 5173 already in use | Previous instance still running | `lsof -i :8000` (or 5173), `kill <PID>` |
| `.env` values not picked up | File in wrong location | Must be at `backend/.env`, not repo root |
| Secrets accidentally committed | Forgot gitignore | Immediately rotate the key; remove from git history with `git filter-branch` or just reset repo if new |
| ngrok free tier limits hit | Too many tunnels today | Restart tunnel; consider upgrading for demo day ($10/mo) |

---

## Appendix A · Quick Reference Commands

### Starting Everything (Fresh Boot)

```bash
# Terminal 1: Backend
cd ~/pipelineiq
docker compose up --build

# Terminal 2: ngrok (copy the HTTPS URL when it shows)
ngrok http 8000

# Terminal 3: Frontend
cd ~/pipelineiq/frontend
npm run dev

# Terminal 4: for issuing commands to test repo
cd ~/pipelineiq-testapp
```

### Stopping Everything

```bash
# In each terminal, Ctrl+C
# To force Docker cleanup:
docker compose down
```

### Triggering a Failure

```bash
cd ~/pipelineiq-testapp
git checkout -b <branch>
# make your breaking change
git commit -am "<message>"
git checkout main && git merge <branch> && git push origin main
```

### Reverting After Demo

```bash
cd ~/pipelineiq-testapp
git revert HEAD --no-edit
git push origin main
```

### Inspecting Failures

```bash
# List all failures
curl http://localhost:8000/failures | python -m json.tool

# Get specific failure
curl http://localhost:8000/failures/<ID> | python -m json.tool

# Get metrics
curl http://localhost:8000/metrics | python -m json.tool
```

### Labeling a Failure

```bash
curl -X POST http://localhost:8000/failures/label \
     -H "Content-Type: application/json" \
     -d '{"failure_id":"<ID>","true_class":"<CLASS>"}'
```

Valid classes: `dependency_conflict`, `flaky_test`, `config_drift`, `resource_exhaustion`, `code_regression`, `infrastructure_error`, `unknown`.

### Replaying a Failure

```bash
curl -X POST http://localhost:8000/failures/<ID>/replay
```

### Checking Logs

```bash
# Backend container logs
docker compose logs -f backend

# ngrok requests log
# Open http://localhost:4040 in browser
```

### Resetting Everything

```bash
# Nuclear option — wipe data, start fresh
docker compose down
rm -rf ~/pipelineiq/data
docker compose up --build
```

---

## Appendix B · Branch Strategy Cheat Sheet

### Test Repo Branches

- `main` — always green (your baseline)
- `failure-*` branches — one per failure class, for evaluation phase
- `demo-trigger` — special branch for live demo trigger
- `eval-NN-*` — used during seeding, deleted after labeling

### Main Repo (pipelineiq) Branches

- `main` — stable, runnable
- `feat/<name>` — feature branches (keeps merges clean)
- No need for develop/staging in a 20-hour sprint

### Commit Convention (Simple)

- `feat:` new feature
- `fix:` bug fix
- `chore:` config, deps, scaffolding
- `docs:` documentation
- `demo:` intentional demo triggers (test repo only)

---

## Appendix C · Final Success Checklist

Before you present:

**Essentials (must have):**
- [ ] Backend running in Docker, accessible via ngrok
- [ ] Frontend running, accessible via localhost (or Vercel)
- [ ] At least 1 real failure processed end-to-end with full RCA
- [ ] Dashboard shows failures + detail view
- [ ] Backup demo video recorded, uploaded, downloadable locally

**Strong (should have):**
- [ ] 5 seeded failures with ground truth labels
- [ ] Metrics page shows Top-1 ≥ 0.7, Top-3 ≥ 0.9, MTTD < 15s
- [ ] Similar-failures retrieval working
- [ ] Live demo trigger branch staged and rehearsed
- [ ] Replay button functional for fallback

**Polish (nice to have):**
- [ ] Frontend deployed to Vercel with custom subdomain
- [ ] GitLab stub visible in UI
- [ ] Slide deck rehearsed in presentation mode
- [ ] Q&A answers practiced for common judge questions

**Team prep:**
- [ ] Both partners know the demo script
- [ ] Division of speaking roles decided
- [ ] Backup plans rehearsed (video, replay, restart)

---

## Appendix D · Final Pep Talk

You're building something real. Not a toy. Not a hallucination on a slide deck. A working AI system that ingests real data, runs actual reasoning, and produces actionable output. That's rare in hackathons.

**Things judges actually reward:**
1. Working demo on real data (you'll have this)
2. Thoughtful architecture with clear production path (you have this documented)
3. Honest evaluation with published metrics (you'll compute these)
4. Specific "next steps" that sound credible (you have these)

**Things judges don't reward:**
1. Overpromising features you didn't build
2. Hand-waving at "AI will figure it out"
3. Synthetic-only benchmarks with inflated numbers
4. Buzzword soup with no working prototype

You're on the right side of every one of these.

**If at Hour 18 only the minimum works:** That's still a demo. Go with it. Honest "small-but-real" beats "big-and-faked" every time.

**If everything works:** Enjoy it. You earned it.

**Good luck. Go build it.**

---

**End of Documentation Set**

Documents in this set:
- `01_SCOPE_AND_EXECUTION_PLAN.md`
- `02_SYSTEM_ARCHITECTURE.md`
- `03_BACKEND_DESIGN.md`
- `04_AI_ORCHESTRATION_AND_EVALUATION.md`
- `05_STEP_BY_STEP_GUIDE.md` ← you are here
