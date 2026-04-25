# app/routers/webhooks.py
import hmac
import hashlib
import uuid
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Header
from app.config import settings
from app.ingestion.github import GitHubIngestor
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
    try:
        import traceback
        ingestor = GitHubIngestor()
        ctx = await ingestor.fetch_context(failure_id, payload)
        orchestrator = RCAOrchestrator()
        rca = await orchestrator.process(ctx)
        await manager.broadcast({"type": "rca_ready", "failure_id": failure_id, "summary": rca.summary})
    except Exception as e:
        print(f"BACKGROUND TASK FAILED for {failure_id}: {str(e)}")
        traceback.print_exc()

@router.post("/gitlab")
async def gitlab_webhook(request: Request):
    payload = await request.json()
    # Stub — log and return. Full integration deferred.
    return {
        "accepted": True,
        "note": "GitLab adapter: stub (full integration in production roadmap)",
        "payload_keys": list(payload.keys()),
    }
