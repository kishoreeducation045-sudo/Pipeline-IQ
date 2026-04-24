# app/ingestion/github.py
import httpx
import zipfile
import io
from app.config import settings
from app.models.failure import FailureContext, LogLine, DiffHunk
from app.normalizer.normalizer import normalize_github

class GitHubIngestor:
    def _make_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {settings.github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=15,
        )

    async def fetch_context(self, failure_id: str, payload: dict) -> FailureContext:
        async with self._make_client() as client:
            run = payload["workflow_run"]
            repo_full = payload["repository"]["full_name"]
            run_id = run["id"]

            logs_text = await self._fetch_logs(client, repo_full, run_id)
            head_sha = run["head_sha"]
            commit_data = await self._fetch_commit(client, repo_full, head_sha)
            diff_hunks = self._parse_diff(commit_data)
            log_lines = self._parse_logs(logs_text)

            return normalize_github(
                failure_id=failure_id,
                payload=payload,
                log_lines=log_lines,
                commit_data=commit_data,
                diff_hunks=diff_hunks,
            )

    async def _fetch_logs(self, client: httpx.AsyncClient, repo: str, run_id: int) -> str:
        url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/logs"
        r = await client.get(url, follow_redirects=True)
        if r.status_code != 200:
            return ""
        # Response is a zip of per-step log files
        try:
            z = zipfile.ZipFile(io.BytesIO(r.content))
            texts = []
            for name in z.namelist():
                with z.open(name) as f:
                    texts.append(f"===== {name} =====\n" + f.read().decode("utf-8", errors="ignore"))
            return "\n".join(texts)
        except zipfile.BadZipFile:
            return r.text

    async def _fetch_commit(self, client: httpx.AsyncClient, repo: str, sha: str) -> dict:
        r = await client.get(f"https://api.github.com/repos/{repo}/commits/{sha}")
        r.raise_for_status()
        return r.json()

    def _parse_diff(self, commit_data: dict) -> list[DiffHunk]:
        hunks = []
        for f in commit_data.get("files", []):
            patch = f.get("patch", "")
            old_lines = [l[1:] for l in patch.splitlines() if l.startswith("-") and not l.startswith("---")]
            new_lines = [l[1:] for l in patch.splitlines() if l.startswith("+") and not l.startswith("+++")]
            status = f.get("status", "modified")
            change_type = {"added": "added", "removed": "deleted"}.get(status, "modified")
            hunks.append(DiffHunk(
                file_path=f["filename"],
                old_lines=old_lines,
                new_lines=new_lines,
                change_type=change_type,
            ))
        return hunks

    def _parse_logs(self, logs_text: str) -> list[LogLine]:
        lines = []
        current_step = "unknown"
        for raw in logs_text.splitlines():
            if raw.startswith("===== "):
                # Step boundary in zip structure
                current_step = raw.strip("= ").strip()
                continue
            level = "info"
            low = raw.lower()
            if "error" in low or "failed" in low or "failure" in low:
                level = "error"
            elif "warning" in low or "warn" in low:
                level = "warning"
            lines.append(LogLine(step=current_step, level=level, message=raw.strip()))
        # Cap to last 500 lines to keep Claude prompt reasonable
        return lines[-500:]
