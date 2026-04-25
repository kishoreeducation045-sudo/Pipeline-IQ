# app/llm/orchestrator.py
import time
import uuid
from datetime import datetime, timezone
from app.detection.hybrid import HybridDetector
from app.detection.flaky import FlakyClassifier
from app.llm.client import gemini
from app.llm.prompts import RCA_SYSTEM_PROMPT, build_user_prompt
from app.models.failure import FailureContext
from app.models.rca import RCAReport, FlakyAssessment
from app.storage.vector import vector_store
from app.storage.db import get_session
from app.storage.models import FailureRow, RCARow

class RCAOrchestrator:
    def __init__(self):
        self.detector = HybridDetector()

    async def process(self, ctx: FailureContext) -> RCAReport:
        start = time.perf_counter()

        # 1. Hybrid detection produces candidates
        candidates = self.detector.detect(ctx, top_k=5)

        # 2. Flaky classification (before Claude call)
        flaky_result = FlakyClassifier().classify(ctx)

        # 3. Retrieve similar past failures from ChromaDB
        query_text = self._failure_signature(ctx)
        similar = vector_store.similar(query_text, k=3)

        # 4. Build prompt (with flaky signals)
        user_prompt = build_user_prompt(ctx, candidates, similar, flaky_result=flaky_result)

        # 5. Call Gemini with structured output
        report: RCAReport = await gemini.generate_json(
            system=RCA_SYSTEM_PROMPT,
            user=user_prompt,
            schema_model=RCAReport,
            max_tokens=2048,
        )

        report.failure_id = ctx.id
        report.generated_at = datetime.now(timezone.utc).isoformat()
        report.latency_ms = int((time.perf_counter() - start) * 1000)
        report.similar_past_failures = [s["id"] for s in similar]

        # 6. Attach flaky assessment
        report.flaky_assessment = FlakyAssessment.model_validate(flaky_result)

        # 7. Persist
        await self._persist(ctx, report)

        # 8. Index in ChromaDB for future retrieval
        vector_store.add(
            failure_id=ctx.id,
            summary_text=f"{report.summary}\n\n{self._failure_signature(ctx)}",
            metadata={
                "failure_class": report.hypotheses[0].failure_class if report.hypotheses else "unknown",
                "repo": ctx.repo_full_name,
                "timestamp": ctx.triggered_at.isoformat(),
            },
        )

        return report

    @staticmethod
    def _failure_signature(ctx: FailureContext) -> str:
        """Concise text used for similarity retrieval."""
        error_lines = [l.message for l in ctx.logs if l.level == "error"][:5]
        changed_files = [f.file_path for f in ctx.diff_hunks][:5]
        return (
            f"Repo: {ctx.repo_full_name} | "
            f"Job: {ctx.job_name} | "
            f"Errors: {' | '.join(error_lines)} | "
            f"Changed: {', '.join(changed_files)}"
        )

    @staticmethod
    async def _persist(ctx: FailureContext, report: RCAReport):
        async with get_session() as session:
            fr = FailureRow(
                id=ctx.id,
                provider=ctx.provider,
                repo_full_name=ctx.repo_full_name,
                workflow_name=ctx.workflow_name,
                job_name=ctx.job_name,
                run_id=ctx.run_id,
                run_url=ctx.run_url,
                conclusion=ctx.conclusion,
                triggered_at=ctx.triggered_at,
                completed_at=ctx.completed_at,
                duration_seconds=ctx.duration_seconds,
                context_json=ctx.model_dump(mode="json"),
            )
            session.add(fr)
            rr = RCARow(
                id=str(uuid.uuid4()),
                failure_id=ctx.id,
                generated_at=datetime.now(timezone.utc),
                summary=report.summary,
                hypotheses_json=[h.model_dump() for h in report.hypotheses],
                recommended_remediation=report.recommended_remediation.model_dump(),
                similar_past_failures=report.similar_past_failures,
                latency_ms=report.latency_ms,
                top1_class=report.hypotheses[0].failure_class if report.hypotheses else "unknown",
            )
            rr.flaky_assessment_json = report.flaky_assessment.model_dump() if report.flaky_assessment else None
            session.add(rr)
            await session.commit()
