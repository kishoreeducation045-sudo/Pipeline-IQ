# app/storage/models.py
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, DateTime, JSON, ForeignKey, Float, Text
from datetime import datetime

class Base(DeclarativeBase):
    pass

class FailureRow(Base):
    __tablename__ = "failures"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    provider: Mapped[str] = mapped_column(String)
    repo_full_name: Mapped[str] = mapped_column(String, index=True)
    workflow_name: Mapped[str] = mapped_column(String)
    job_name: Mapped[str] = mapped_column(String)
    run_id: Mapped[str] = mapped_column(String)
    run_url: Mapped[str] = mapped_column(String)
    conclusion: Mapped[str] = mapped_column(String)
    triggered_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime)
    duration_seconds: Mapped[int] = mapped_column(Integer)
    context_json: Mapped[dict] = mapped_column(JSON)  # Full FailureContext
    rca: Mapped["RCARow"] = relationship(back_populates="failure", uselist=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "provider": self.provider,
            "repo_full_name": self.repo_full_name,
            "workflow_name": self.workflow_name,
            "job_name": self.job_name,
            "run_id": self.run_id,
            "run_url": self.run_url,
            "conclusion": self.conclusion,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "context_json": self.context_json,
        }

class RCARow(Base):
    __tablename__ = "rca_reports"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    failure_id: Mapped[str] = mapped_column(String, ForeignKey("failures.id"), index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime)
    summary: Mapped[str] = mapped_column(Text)
    hypotheses_json: Mapped[list] = mapped_column(JSON)
    recommended_remediation: Mapped[dict] = mapped_column(JSON)
    similar_past_failures: Mapped[list] = mapped_column(JSON, default=list)
    latency_ms: Mapped[int] = mapped_column(Integer)
    top1_class: Mapped[str] = mapped_column(String, index=True)
    ground_truth_class: Mapped[str | None] = mapped_column(String, nullable=True)
    failure: Mapped[FailureRow] = relationship(back_populates="rca")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "failure_id": self.failure_id,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "summary": self.summary,
            "hypotheses_json": self.hypotheses_json,
            "recommended_remediation": self.recommended_remediation,
            "similar_past_failures": self.similar_past_failures,
            "latency_ms": self.latency_ms,
            "top1_class": self.top1_class,
            "ground_truth_class": self.ground_truth_class,
        }

class MetricsSnapshotRow(Base):
    __tablename__ = "metrics_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    top1_accuracy: Mapped[float] = mapped_column(Float)
    top3_accuracy: Mapped[float] = mapped_column(Float)
    mttd_ms: Mapped[int] = mapped_column(Integer)
    sample_size: Mapped[int] = mapped_column(Integer)
