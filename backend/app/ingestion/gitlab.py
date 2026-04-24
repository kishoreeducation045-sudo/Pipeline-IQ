# app/ingestion/gitlab.py
from app.models.failure import FailureContext

class GitLabIngestor:
    async def fetch_context(self, failure_id: str, payload: dict) -> FailureContext | None:
        # Stub — real integration would mirror GitHub ingestor.
        # Returns None to signal "received but not processed".
        return None
