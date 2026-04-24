# app/evaluation/metrics.py
from datetime import datetime
from sqlalchemy import select
from app.storage.db import get_session
from app.storage.models import RCARow, MetricsSnapshotRow

async def compute_metrics() -> dict:
    async with get_session() as session:
        rcas = (await session.execute(
            select(RCARow).where(RCARow.ground_truth_class.isnot(None))
        )).scalars().all()

        if not rcas:
            return {
                "top1_accuracy": None,
                "top3_accuracy": None,
                "mttd_ms": None,
                "sample_size": 0,
                "note": "No labeled cases yet",
            }

        top1_correct = 0
        top3_correct = 0
        latencies = []
        for r in rcas:
            hyp_classes = [h["failure_class"] for h in r.hypotheses_json]
            if hyp_classes and hyp_classes[0] == r.ground_truth_class:
                top1_correct += 1
            if r.ground_truth_class in hyp_classes[:3]:
                top3_correct += 1
            latencies.append(r.latency_ms)

        n = len(rcas)
        metrics = {
            "top1_accuracy": round(top1_correct / n, 3),
            "top3_accuracy": round(top3_correct / n, 3),
            "mttd_ms": int(sum(latencies) / n),
            "sample_size": n,
        }

        # Snapshot for history
        session.add(MetricsSnapshotRow(
            timestamp=datetime.utcnow(),
            top1_accuracy=metrics["top1_accuracy"],
            top3_accuracy=metrics["top3_accuracy"],
            mttd_ms=metrics["mttd_ms"],
            sample_size=n,
        ))
        await session.commit()
        return metrics


async def label_ground_truth(failure_id: str, true_class: str) -> None:
    async with get_session() as session:
        rca = (await session.execute(
            select(RCARow).where(RCARow.failure_id == failure_id)
        )).scalar_one()
        rca.ground_truth_class = true_class
        await session.commit()
