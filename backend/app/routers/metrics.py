# app/routers/metrics.py
from fastapi import APIRouter
from app.evaluation.metrics import compute_metrics

router = APIRouter(prefix="/metrics", tags=["metrics"])

@router.get("")
async def get_metrics():
    return await compute_metrics()
