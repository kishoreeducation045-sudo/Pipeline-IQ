# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.config import settings
from app.routers import webhooks, failures, metrics
from app.storage.db import init_db
from app.ws.manager import manager
from app.evaluation.seed import seed_failures
from app.evaluation.metrics import compute_metrics, label_ground_truth

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


# ── Evaluation endpoints (Doc 3 §4.1, Doc 4 §5.6) ──────────────────────────

class LabelRequest(BaseModel):
    failure_id: str
    true_class: str

@app.post("/eval/seed", tags=["eval"])
async def eval_seed():
    await seed_failures()
    return {"seeded": 5}

@app.post("/eval/run", tags=["eval"])
async def eval_run():
    return await compute_metrics()

@app.post("/eval/label", tags=["eval"])
async def eval_label(body: LabelRequest):
    await label_ground_truth(body.failure_id, body.true_class)
    return {"labeled": True}
