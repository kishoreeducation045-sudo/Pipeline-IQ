# app/normalizer/normalizer.py
from datetime import datetime
from app.models.failure import FailureContext, CommitInfo

def normalize_github(failure_id, payload, log_lines, commit_data, diff_hunks) -> FailureContext:
    run = payload["workflow_run"]
    repo = payload["repository"]
    commit = commit_data["commit"]
    return FailureContext(
        id=failure_id,
        provider="github",
        repo_full_name=repo["full_name"],
        workflow_name=run["name"],
        job_name=run.get("display_title", run["name"]),
        run_id=str(run["id"]),
        run_url=run["html_url"],
        conclusion=run["conclusion"],
        triggered_at=datetime.fromisoformat(run["created_at"].replace("Z", "+00:00")),
        completed_at=datetime.fromisoformat(run["updated_at"].replace("Z", "+00:00")),
        duration_seconds=int(
            (datetime.fromisoformat(run["updated_at"].replace("Z", "+00:00"))
             - datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))).total_seconds()
        ),
        head_commit=CommitInfo(
            sha=commit_data["sha"],
            author=commit["author"]["name"],
            message=commit["message"],
            timestamp=datetime.fromisoformat(commit["author"]["date"].replace("Z", "+00:00")),
            files_changed=[f["filename"] for f in commit_data.get("files", [])],
        ),
        recent_commits=[],
        logs=log_lines,
        diff_hunks=diff_hunks,
        test_results=[],
        raw_payload=payload,
    )


def normalize_gitlab(failure_id, payload, log_lines, commit_data, diff_hunks) -> FailureContext | None:
    # Stub — mirrors normalize_github signature; returns None until full GitLab adapter is built.
    return None
