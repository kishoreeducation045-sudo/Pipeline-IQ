# PipelineIQ — Prototype Scope & Execution Plan

**Document 1 of 4** · Hackathon: GitLab-DevOps Track, RV College Bangalore · Duration: 20 hours · Team: 2

---

## 1. Hero Demo (The One Thing Judges Will Remember)

> A GitHub Actions CI pipeline fails in real time during our demo. Within 15 seconds, our dashboard shows three ranked root-cause hypotheses, each with evidence pulled from the actual logs, a plain-English explanation written by Claude, and a suggested remediation. We then show the same engine analyzing 3 other pre-seeded real failures. We finish with a live metrics panel: Top-1 accuracy, mean time to diagnosis, and a "similar past failures" retrieval demonstration.

Every scope decision below protects this demo.

---

## 2. Scope: What We Are Building

### ✅ IN SCOPE (Prototype Must-Haves)

| Capability | What It Means |
|---|---|
| **GitHub Actions webhook ingestion** | Receive real pipeline failure events from a test repo |
| **Log + diff + test report extraction** | Pull actual failure data via GitHub API |
| **Failure correlation graph** | NetworkX graph connecting commits, tests, services, deps |
| **Hybrid anomaly detection** | Rule-based + graph centrality + Claude reasoning |
| **Claude-generated RCA report** | Plain-English explanation with evidence snippets |
| **Remediation suggestions** | Actionable fix recommendations (suggest only, do not execute) |
| **Similar-failures retrieval** | ChromaDB-backed "have we seen this before" lookup |
| **Live React dashboard** | Failure feed, RCA detail view, metrics panel |
| **Evaluation against 3–5 real failures** | Pre-seeded real GitHub Actions failures with ground truth |
| **GitLab webhook stub** | Empty adapter proving extensibility (no real integration) |
| **Docker containerization** | Backend runs in Docker for reproducibility |
| **ngrok tunnel** | Public HTTPS URL for webhook delivery + judge access |

### ❌ OUT OF SCOPE (Explicitly Deferred, With Why)

| Deferred Capability | Why We Are Skipping | Production Path |
|---|---|---|
| Real Jaeger/Prometheus integration | 4+ hours for marginal demo value | Adapter interfaces already defined; swap mock for real in 1 day |
| Automated remediation execution | Safety review required; 6+ hrs | Human-in-the-loop approval flow, Phase 2 |
| LSTM time-series anomaly detection | Cannot train meaningfully in 20 hrs | Hybrid approach is genuinely stronger for the prototype |
| Full GitLab CI integration | GitHub is our test bed; 3 hrs saved | Adapter pattern ready; 1-day port |
| Neo4j graph database | Setup + Cypher learning = 4 hrs | NetworkX wrapped in `GraphStore` interface; swap in 1 day |
| User authentication / multi-tenancy | Not a judge priority | OAuth + tenant isolation, Phase 2 |
| Production deployment (Railway, K8s) | 3+ hours of cloud debugging | Docker image is cloud-ready |
| Historical trend analytics dashboard | UI-heavy, not core story | Metrics stored in SQLite; build UI post-hackathon |
| Slack/email notification delivery | Trivial but not core | Webhook out in 2 hrs post-hackathon |

**Scope Creep Rule:** If someone suggests adding any OUT-OF-SCOPE item during the hackathon, the answer is automatically "not for the prototype, in the production roadmap." Point them to this document.

---

## 3. Pre-Flight Checklist (Hour 0 — Before Writing Any Code)

**Both of you, together, in the same room or call, complete this in the first hour. If anything fails here, you need to know NOW, not at hour 15.**

### Accounts & Keys
- [ ] **Anthropic API account**: sign up at https://console.anthropic.com
- [ ] **Add $10 credit** to Anthropic account (covers prototype + demo + buffer)
- [ ] **Generate API key** → save in a shared password manager or secure doc
- [ ] **ngrok account**: sign up at https://ngrok.com (free tier)
- [ ] **Install ngrok CLI** on BOTH laptops: https://ngrok.com/download
- [ ] **Authenticate ngrok** on both laptops: `ngrok config add-authtoken <token>`
- [ ] **Vercel account** (optional but recommended): https://vercel.com — connect to GitHub
- [ ] **GitHub account** ready with SSH key configured

### Local Environment
- [ ] **Python 3.11+** installed on both laptops: `python --version`
- [ ] **Node.js 18+** installed on both laptops: `node --version`
- [ ] **Docker Desktop** running on both laptops: `docker --version` and `docker ps`
- [ ] **Git** configured with user email/name on both laptops
- [ ] **Code editor** ready (VS Code recommended)

### Fresh Test Repo
- [ ] Create NEW GitHub repo: `pipelineiq-testapp` (public, initialized with README)
- [ ] Clone to both laptops
- [ ] Verify you can push a commit successfully

### Main Project Repo
- [ ] Create NEW GitHub repo: `pipelineiq` (private if preferred)
- [ ] Clone to both laptops
- [ ] Create basic folder structure (see Document 2 & 3)
- [ ] Add `.gitignore` for Python + Node
- [ ] Protect secrets: add `.env` to `.gitignore` immediately

### Communication & Coordination
- [ ] Shared Slack/Discord/WhatsApp thread for updates
- [ ] Agreed on branching strategy: `main` + feature branches, PRs required before merge
- [ ] Agreed on commit convention: `feat:`, `fix:`, `chore:` prefixes

**If any item fails:** STOP and resolve before moving to Hour 1. Debugging a broken Docker install at Hour 10 will destroy your hackathon.

---

## 4. Hour-by-Hour Execution Roadmap

**Legend:**
- 👤 **Partner A (You)** — Backend/AI lead (stronger in backend)
- 🎨 **Partner B (Teammate)** — Frontend/Integration lead (stronger in frontend)
- 🤝 **Both** — Pairing or parallel tasks

### Hours 0–2: Foundation

| Time | 👤 Partner A | 🎨 Partner B |
|---|---|---|
| 0:00–1:00 | Pre-flight checklist (together) | Pre-flight checklist (together) |
| 1:00–2:00 | FastAPI project scaffold, Dockerfile, docker-compose.yml, Claude SDK connection test | React+Vite+Tailwind+shadcn scaffold, test GitHub repo creation, paste dummy Flask app |

**Exit criteria:** FastAPI responds on `localhost:8000/health`. React runs on `localhost:5173`. Test repo exists with Flask app visible on GitHub.

### Hours 2–6: Core Engine

| Time | 👤 Partner A | 🎨 Partner B |
|---|---|---|
| 2:00–3:30 | Data ingestion layer: webhook parser, GitHub API client for logs | GitHub Actions CI YAML (copy from Doc 3), push to test repo, verify green build |
| 3:30–5:00 | Normalization layer: unified failure schema (Pydantic models) | Dashboard shell: routes, sidebar, empty failure list component |
| 5:00–6:00 | NetworkX graph builder, node/edge schema implementation | Webhook receiver endpoint stub (`POST /webhook/github`), test with ngrok |

**Exit criteria:** ngrok tunnel running. Pushing a bad commit to test repo triggers webhook, which arrives at backend, which stores raw payload.

### Hours 6–10: AI Layer & Integration

| Time | 👤 Partner A | 🎨 Partner B |
|---|---|---|
| 6:00–7:30 | Rule-based anomaly detectors (dependency conflict, test failure, syntax error patterns) | Failure list UI → live-polls `/failures` endpoint |
| 7:30–9:00 | Claude prompt engineering: RCA generation + remediation suggestion | Failure detail page: render RCA report + evidence snippets |
| 9:00–10:00 | Graph centrality ranker + hypothesis scoring | Dashboard polish: loading states, error handling |

**Exit criteria:** End-to-end flow works: bad commit → webhook → RCA generated → visible on dashboard. At least one real failure fully explained.

### Hours 10–12: Mandatory Break

**SLEEP OR REST. Do not skip this.** You cannot present well if you are exhausted. Stagger if needed (one sleeps while other finishes non-critical polish), but both should get rest.

### Hours 12–16: Evaluation & History

| Time | 👤 Partner A | 🎨 Partner B |
|---|---|---|
| 12:00–13:30 | ChromaDB setup + similar-failure retrieval | Metrics panel UI (Top-1, Top-3, MTTD display) |
| 13:30–15:00 | Evaluation harness: pre-seed 3–5 real failures, record ground truth, compute metrics | Historical failure view + trend chart |
| 15:00–16:00 | Tune Claude prompts based on eval results | GitLab webhook stub endpoint + UI label "GitLab adapter ready" |

**Exit criteria:** Metrics dashboard shows real numbers. At least 3 real failures pre-seeded and correctly diagnosed.

### Hours 16–18: Polish & Live Demo Prep

| Time | 👤 Partner A | 🎨 Partner B |
|---|---|---|
| 16:00–17:00 | Final prompt tuning, edge case handling, error states | UI polish, smooth transitions, "wow" moments (animations on RCA reveal) |
| 17:00–18:00 | Full demo rehearsal (2–3 runs) — time the flow | Full demo rehearsal with Partner A |

**Exit criteria:** Demo flows end-to-end in under 5 minutes. Both of you can run it.

### Hours 18–19: Slides & Recorded Backup

| Time | 🤝 Both |
|---|---|
| 18:00–18:30 | Record full demo video as backup (use OBS or QuickTime). Upload to Google Drive, get sharable link. |
| 18:30–19:00 | 5 slides max: Problem → Solution → Architecture → Metrics → Demo. Content is in docs, just paste. |

### Hour 19–20: Buffer

| Time | 🤝 Both |
|---|---|
| 19:00–19:30 | Final demo rehearsal. Test: kill backend, bring it back up. Kill ngrok, reconnect. Practice failures gracefully. |
| 19:30–20:00 | Rest. Eat. Hydrate. Mental prep. |

---

## 5. Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | Anthropic API rate limits during demo | Medium | High | Pre-cache RCA responses for all seeded failures; implement retry with exponential backoff |
| 2 | ngrok free tier URL changes on restart | High | Medium | Don't restart ngrok unless necessary; use ngrok `--subdomain` if upgraded, or update GitHub webhook URL if needed |
| 3 | GitHub Actions slow to run during live demo | Medium | High | Keep recorded video backup; have "replay last failure" button in UI |
| 4 | Wifi/internet drops during demo | Low | Catastrophic | Pre-cached responses work offline; video backup on local disk; hotspot from phone as backup |
| 5 | Both partners sleep through alarm at hour 12 | Medium | Medium | Set multiple alarms; tell someone to wake you |
| 6 | Scope creep: "let's add Neo4j" at 3 AM | High | High | This document. Point to Scope-Out table. Vote required to add anything |
| 7 | Merge conflicts on shared files | Medium | Low | Clean backend/frontend boundary; `main` protected; communicate before editing shared files |
| 8 | Claude prompt returns malformed JSON | Medium | Medium | Use Pydantic validation + retry with "please fix this JSON" prompt as fallback |
| 9 | Docker fails to start on one laptop | Low | High | Have non-Docker fallback: run FastAPI directly with `uvicorn` |
| 10 | GitHub webhook secret mismatch | Medium | Medium | Document exact setup steps (see Doc 3); test webhook with `curl` first |

---

## 6. Demo Script (5-Minute Presentation)

**Speaker roles: alternate between A and B for energy. Judges retain more when two people present.**

### Minute 0:00–0:45 — The Problem (Partner A speaks)

> "Imagine your production CI/CD pipeline just broke. Senior engineers will spend 2–6 hours digging through logs across hundreds of microservices to find the root cause. That's hours of blocked deployments, missed SLAs, and burned-out engineers. Every day, across the industry, billions are lost to this one broken workflow.
>
> We built **PipelineIQ** — an AI engine that does in 15 seconds what engineers do in 6 hours."

### Minute 0:45–1:30 — The Solution (Partner B speaks)

> "PipelineIQ plugs into your CI/CD system. When a pipeline fails, it ingests the logs, traces, test reports, and code diffs in real time. It builds a failure correlation graph, runs hybrid anomaly detection — rule-based + graph centrality + Claude reasoning — and generates a ranked root-cause report with evidence.
>
> Let me show you."

### Minute 1:30–3:30 — Live Demo (Partner A drives, Partner B narrates)

1. **Partner A**: Opens terminal, has bad commit staged. Shows dashboard first — empty state.
2. **Partner A**: "I'm going to push a commit that breaks our CI pipeline. Watch the dashboard."
3. **Partner A**: `git push origin main` (pre-prepared commit with dependency conflict)
4. **Partner B (narrating while waiting)**: "GitHub Actions is now running. When it fails, a webhook fires to our engine. Our engine will pull the failure data, build the correlation graph, query Claude for root-cause reasoning, and render the result. Target: under 15 seconds."
5. Dashboard updates live — failure appears, then RCA populates.
6. **Partner B**: "Top hypothesis: dependency version conflict in `requirements.txt`. Confidence 94%. Evidence: the `pip install` log shows `ERROR: No matching distribution found for requests==3.0.0`. Remediation: pin `requests` to `2.31.0` or latest stable."
7. **Partner A**: Clicks into failure detail. Shows evidence panel with actual log snippets highlighted.

### Minute 3:30–4:15 — Metrics & Depth (Partner B speaks)

1. Navigate to Metrics panel.
2. "We tested against 5 real GitHub Actions pipeline failures — not synthetic templates. Top-1 accuracy: 80%. Top-3 accuracy: 100%. Mean time to diagnosis: 11 seconds."
3. Navigate to Similar Failures view.
4. "PipelineIQ learns over time. When a new failure comes in, we retrieve similar past failures via ChromaDB to give Claude richer context. The system gets smarter with every incident."

### Minute 4:15–5:00 — The Moat & Ask (Partner A speaks)

> "Three things make this defensible: First, we don't just detect failures — we explain them with evidence. Second, our hybrid detection — rules + graph + LLM — is more accurate than any single approach. Third, we learn institutional memory automatically.
>
> In production: swap NetworkX for Neo4j, add Jaeger/Prometheus, wire up auto-remediation with human approval. The adapters are already built.
>
> That's PipelineIQ. Questions?"

---

## 7. Live Demo Failure Trigger Guide

**Goal:** Reliably trigger a real CI failure during the 5-minute demo window.

### Pre-Demo Setup (do this at Hour 16)

1. **Test repo clean state**: Pull latest main on test repo. Confirm green build.
2. **Prepare the "demo commit" on a branch**:
   ```bash
   cd ~/pipelineiq-testapp
   git checkout -b demo-trigger
   # Edit requirements.txt to introduce a bad version
   echo "requests==99.99.99" >> requirements.txt
   git add requirements.txt
   git commit -m "demo: trigger dependency conflict"
   # DO NOT PUSH YET — this is staged for the demo
   ```
3. **Verify webhook is live**: push a throwaway commit first, confirm it arrives at backend. Then reset.
4. **Warm up Claude**: send one test RCA request so cold-start latency is already paid.

### During Demo

1. Terminal already open, `demo-trigger` branch checked out.
2. Say your line, then run:
   ```bash
   git checkout main
   git merge demo-trigger
   git push origin main
   ```
3. Switch immediately to browser with dashboard open.
4. Expected timeline:
   - 0–5 sec: GitHub Actions starts
   - 5–20 sec: Job runs, pip install fails
   - 20–25 sec: Webhook fires
   - 25–35 sec: Backend ingests, Claude responds
   - 35–40 sec: Dashboard updates with RCA

**Total expected: ~40 seconds from push to visible RCA.** Plan narration to fill the wait.

### Backup Plan If Live Trigger Fails

1. **Plan B: Replay Button** — If webhook doesn't fire in 60 seconds, click the "Replay Last Failure" button in the dashboard. This re-runs the RCA on a pre-cached failure. Narrate: "Looks like GitHub Actions is running slowly today. Let me show you a failure we triggered earlier — same engine, same result."
2. **Plan C: Recorded Video** — If dashboard itself is broken, switch to pre-recorded demo video. Narrate over it.

### Post-Demo Cleanup

After the demo, reset your test repo:
```bash
git revert HEAD --no-edit
git push origin main
```

This keeps the repo ready for the next demo (some hackathons ask for multiple presentations).

---

## 8. Recorded Video Backup Plan

**Do this between Hours 18:00 and 18:30.**

### Recording Setup
- **Tool**: OBS Studio (free, cross-platform) or QuickTime (Mac built-in)
- **Resolution**: 1920x1080, 30fps
- **Audio**: USB mic if available, else laptop mic in quiet room
- **Browser window**: Full-screen Chrome with dashboard open
- **Terminal**: Separate recording or picture-in-picture

### Script to Record
Run through the full 5-minute demo script (Section 6 above). Record in one take if possible. Keep retakes to 2 max.

### Post-Recording
- [ ] Upload to Google Drive (sharable link)
- [ ] Upload to YouTube as UNLISTED (backup sharable link)
- [ ] Download MP4 to local laptop (plays without internet)
- [ ] Test playback on both laptops
- [ ] Include link in slides as "Backup Demo" slide

---

## 9. Success Criteria (What "Done" Looks Like at Hour 20)

**Minimum viable demo (non-negotiable):**
- [ ] At least 1 real pipeline failure flows end-to-end (webhook → RCA → dashboard)
- [ ] Dashboard renders without errors
- [ ] Claude-generated RCA report shows evidence snippets
- [ ] Remediation suggestion visible
- [ ] Backend runs in Docker
- [ ] ngrok tunnel accessible publicly
- [ ] Recorded video backup exists

**Strong demo (target):**
- [ ] 3–5 pre-seeded real failures, all correctly diagnosed
- [ ] Metrics panel shows Top-1, Top-3, MTTD
- [ ] Similar-failures retrieval working
- [ ] Live-triggered failure works in rehearsals
- [ ] Frontend on Vercel with custom subdomain
- [ ] GitLab stub visible in UI

**Stretch (only if on track by Hour 16):**
- [ ] Failure trend chart (last 10 failures over time)
- [ ] Dashboard responsive on mobile
- [ ] Multiple failure classes demonstrated in rehearsal

---

## 10. Timeline Infographic

```
┌──────────────────────────────────────────────────────────────────────────┐
│                  PipelineIQ — 20 Hour Execution Timeline                 │
├─────┬──────────────────────────────┬─────────────────────────────────────┤
│ Hr  │ 👤 Partner A (Backend/AI)    │ 🎨 Partner B (Frontend/Integration) │
├─────┼──────────────────────────────┼─────────────────────────────────────┤
│ 0-1 │ ████ Pre-flight checklist (together) ████                          │
│ 1-2 │ FastAPI + Docker scaffold    │ React + test repo setup             │
│ 2-3 │ Webhook parser               │ GitHub Actions YAML                 │
│ 3-4 │ Normalization layer          │ Dashboard shell                     │
│ 4-5 │ Normalization layer          │ Dashboard shell                     │
│ 5-6 │ NetworkX graph builder       │ Webhook receiver + ngrok test       │
│ 6-7 │ Rule-based detectors         │ Failure list UI                     │
│ 7-8 │ Claude prompt engineering    │ Failure list UI                     │
│ 8-9 │ Claude prompt engineering    │ Failure detail page                 │
│ 9-10│ Graph ranker                 │ Dashboard polish                    │
│10-12│ ████████████ SLEEP / BREAK ████████████                            │
│12-13│ ChromaDB + similar failures  │ Metrics panel UI                    │
│13-14│ Evaluation harness           │ Historical view                     │
│14-15│ Seed 3-5 real failures       │ Historical view                     │
│15-16│ Prompt tuning                │ GitLab stub + label                 │
│16-17│ Edge cases + error handling  │ UI polish + animations              │
│17-18│ ████ Demo rehearsal (together) ████                                │
│18-19│ ████ Record video + slides (together) ████                         │
│19-20│ ████ Buffer + rest (together) ████                                 │
└─────┴──────────────────────────────┴─────────────────────────────────────┘
```

---

## 11. Emergency Contacts (Fill In Before Hackathon)

| Who | Role | Contact | When to Call |
|---|---|---|---|
| Your partner | Co-builder | _fill_in_ | Always |
| Mentor/hackathon organizer | Escalation | _fill_in_ | Blocker > 1 hour |
| Anthropic support | API issues | support@anthropic.com | API down |
| GitHub support | Actions issues | https://support.github.com | Webhooks not firing |

---

**Next Document**: [02_SYSTEM_ARCHITECTURE.md](./02_SYSTEM_ARCHITECTURE.md)
