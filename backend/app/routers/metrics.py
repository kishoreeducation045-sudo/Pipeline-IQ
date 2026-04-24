# app/routers/metrics.py
from fastapi import APIRouter
from sqlalchemy import select, func
from app.evaluation.metrics import compute_metrics
from app.storage.db import get_session
from app.storage.models import RCARow
from app.config import settings

router = APIRouter(prefix="/metrics", tags=["metrics"])

@router.get("")
async def get_metrics():
    return await compute_metrics()

@router.get("/roi")
async def get_roi():
    async with get_session() as session:
        # Total failures processed
        failures_processed = (await session.execute(
            select(func.count()).select_from(RCARow)
        )).scalar() or 0

        # Count flaky-classified failures
        all_rcas = (await session.execute(select(RCARow))).scalars().all()
        flaky_caught = 0
        for rca in all_rcas:
            if rca.flaky_assessment_json and rca.flaky_assessment_json.get("is_flaky"):
                flaky_caught += 1

    if failures_processed == 0:
        return {
            "failures_processed": 0,
            "flaky_caught": 0,
            "minutes_saved": 0,
            "hours_saved": 0.0,
            "money_saved_usd": 0.0,
            "llm_cost_usd": 0.0,
            "net_savings_usd": 0.0,
            "roi_multiplier": 0,
            "assumptions": {
                "minutes_saved_per_failure": settings.minutes_saved_per_failure,
                "dev_hourly_usd": settings.dev_hourly_usd,
                "llm_cost_per_rca_usd": settings.llm_cost_per_rca_usd,
            },
            "note": "Process failures to see ROI.",
        }

    minutes_saved = failures_processed * settings.minutes_saved_per_failure + flaky_caught * 30
    hours_saved = round(minutes_saved / 60, 2)
    money_saved_usd = round(hours_saved * settings.dev_hourly_usd, 2)
    llm_cost_usd = round(failures_processed * settings.llm_cost_per_rca_usd, 2)
    net_savings_usd = round(money_saved_usd - llm_cost_usd, 2)
    roi_multiplier = round(money_saved_usd / llm_cost_usd, 1) if llm_cost_usd > 0 else 0

    return {
        "failures_processed": failures_processed,
        "flaky_caught": flaky_caught,
        "minutes_saved": minutes_saved,
        "hours_saved": hours_saved,
        "money_saved_usd": money_saved_usd,
        "llm_cost_usd": llm_cost_usd,
        "net_savings_usd": net_savings_usd,
        "roi_multiplier": roi_multiplier,
        "assumptions": {
            "minutes_saved_per_failure": settings.minutes_saved_per_failure,
            "dev_hourly_usd": settings.dev_hourly_usd,
            "llm_cost_per_rca_usd": settings.llm_cost_per_rca_usd,
        },
    }
