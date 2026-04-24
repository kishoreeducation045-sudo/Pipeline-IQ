# app/routers/failures.py
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from app.storage.db import get_session
from app.storage.models import FailureRow, RCARow

router = APIRouter(prefix="/failures", tags=["failures"])

@router.get("")
async def list_failures(limit: int = Query(default=20, le=100)):
    async with get_session() as session:
        rows = (await session.execute(
            select(FailureRow).options(selectinload(FailureRow.rca)).order_by(desc(FailureRow.triggered_at)).limit(limit)

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
                "is_flaky": (r.rca.flaky_assessment_json or {}).get("is_flaky", False) if r.rca and r.rca.flaky_assessment_json else False,
            }
            for r in rows
        ]

@router.get("/{failure_id}")
async def failure_detail(failure_id: str):
    async with get_session() as session:
        row = (await session.execute(
            select(FailureRow).options(selectinload(FailureRow.rca)).where(FailureRow.id == failure_id)

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
