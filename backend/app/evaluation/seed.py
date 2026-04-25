# app/evaluation/seed.py
from app.models.failure import FailureContext, LogLine, DiffHunk, CommitInfo
from datetime import datetime, timedelta

def synthetic_dependency_failure() -> FailureContext:
    return FailureContext(
        id="synth-dep-1",
        provider="github",
        repo_full_name="pipelineiq/testapp",
        workflow_name="CI",
        job_name="build-and-test",
        run_id="12345",
        run_url="https://github.com/pipelineiq/testapp/actions/runs/12345",
        conclusion="failure",
        triggered_at=datetime.utcnow() - timedelta(seconds=30),
        completed_at=datetime.utcnow(),
        duration_seconds=30,
        head_commit=CommitInfo(
            sha="abc123",
            author="testuser",
            message="chore: bump requests",
            timestamp=datetime.utcnow(),
            files_changed=["requirements.txt"],
        ),
        logs=[
            LogLine(step="Install dependencies", level="info",
                    message="Collecting requests==99.99.99"),
            LogLine(step="Install dependencies", level="error",
                    message="ERROR: Could not find a version that satisfies the requirement requests==99.99.99"),
            LogLine(step="Install dependencies", level="error",
                    message="ERROR: No matching distribution found for requests==99.99.99"),
        ],
        diff_hunks=[
            DiffHunk(
                file_path="requirements.txt",
                old_lines=["requests==2.31.0"],
                new_lines=["requests==99.99.99"],
                change_type="modified",
            )
        ],
        raw_payload={},
    )

def synthetic_syntax_error_failure() -> FailureContext:
    """eval-02: code_regression — SyntaxError in app.py (Doc 3 §9.2)."""
    return FailureContext(
        id="synth-syntax-2",
        provider="github",
        repo_full_name="pipelineiq/testapp",
        workflow_name="CI",
        job_name="build-and-test",
        run_id="12346",
        run_url="https://github.com/pipelineiq/testapp/actions/runs/12346",
        conclusion="failure",
        triggered_at=datetime.utcnow() - timedelta(seconds=20),
        completed_at=datetime.utcnow(),
        duration_seconds=20,
        head_commit=CommitInfo(
            sha="def456",
            author="testuser",
            message="feat: refactor add (demo syntax break)",
            timestamp=datetime.utcnow(),
            files_changed=["app.py"],
        ),
        logs=[
            LogLine(step="Lint (syntax check)", level="info",
                    message="python -m py_compile app.py"),
            LogLine(step="Lint (syntax check)", level="error",
                    message="  File \"app.py\", line 10"),
            LogLine(step="Lint (syntax check)", level="error",
                    message="    return a +  # intentional syntax error"),
            LogLine(step="Lint (syntax check)", level="error",
                    message="SyntaxError: invalid syntax"),
        ],
        diff_hunks=[
            DiffHunk(
                file_path="app.py",
                old_lines=["    return a + b"],
                new_lines=["    return a +  # intentional syntax error"],
                change_type="modified",
            )
        ],
        raw_payload={},
    )


def synthetic_test_assertion_failure() -> FailureContext:
    """eval-03: code_regression — multiply() logic broken, test_multiply fails (Doc 3 §9.3)."""
    return FailureContext(
        id="synth-test-3",
        provider="github",
        repo_full_name="pipelineiq/testapp",
        workflow_name="CI",
        job_name="build-and-test",
        run_id="12347",
        run_url="https://github.com/pipelineiq/testapp/actions/runs/12347",
        conclusion="failure",
        triggered_at=datetime.utcnow() - timedelta(seconds=45),
        completed_at=datetime.utcnow(),
        duration_seconds=45,
        head_commit=CommitInfo(
            sha="ghi789",
            author="testuser",
            message="refactor: simplify multiply logic",
            timestamp=datetime.utcnow(),
            files_changed=["app.py"],
        ),
        logs=[
            LogLine(step="Run tests", level="info",
                    message="collected 4 items"),
            LogLine(step="Run tests", level="error",
                    message="FAILED tests/test_app.py::test_multiply - AssertionError: assert 9 == 20"),
            LogLine(step="Run tests", level="error",
                    message="short test summary info"),
            LogLine(step="Run tests", level="error",
                    message="FAILED tests/test_app.py::test_multiply"),
            LogLine(step="Run tests", level="error",
                    message="1 failed, 3 passed in 0.42s"),
        ],
        diff_hunks=[
            DiffHunk(
                file_path="app.py",
                old_lines=["    return a * b"],
                new_lines=["    return a + b  # wrong operation"],
                change_type="modified",
            )
        ],
        raw_payload={},
    )


def synthetic_config_drift_failure() -> FailureContext:
    """eval-04: config_drift — Python 2.7 unsupported in setup-python@v5 (Doc 3 §9.4)."""
    return FailureContext(
        id="synth-config-4",
        provider="github",
        repo_full_name="pipelineiq/testapp",
        workflow_name="CI",
        job_name="build-and-test",
        run_id="12348",
        run_url="https://github.com/pipelineiq/testapp/actions/runs/12348",
        conclusion="failure",
        triggered_at=datetime.utcnow() - timedelta(seconds=15),
        completed_at=datetime.utcnow(),
        duration_seconds=15,
        head_commit=CommitInfo(
            sha="jkl012",
            author="testuser",
            message="ci: pin python version",
            timestamp=datetime.utcnow(),
            files_changed=[".github/workflows/ci.yml"],
        ),
        logs=[
            LogLine(step="Set up Python", level="info",
                    message="Set up Python 2.7"),
            LogLine(step="Set up Python", level="error",
                    message="Version 2.7 was not found in the local cache or downloaded."),
            LogLine(step="Set up Python", level="error",
                    message="Version 2.7 is not available on ubuntu-latest."),
        ],
        diff_hunks=[
            DiffHunk(
                file_path=".github/workflows/ci.yml",
                old_lines=['          python-version: "3.11"'],
                new_lines=['          python-version: "2.7"'],
                change_type="modified",
            )
        ],
        raw_payload={},
    )


def synthetic_resource_exhaustion_failure() -> FailureContext:
    """eval-05: resource_exhaustion — step timed out (exit 124) (Doc 3 §9.5)."""
    return FailureContext(
        id="synth-resource-5",
        provider="github",
        repo_full_name="pipelineiq/testapp",
        workflow_name="CI",
        job_name="build-and-test",
        run_id="12349",
        run_url="https://github.com/pipelineiq/testapp/actions/runs/12349",
        conclusion="failure",
        triggered_at=datetime.utcnow() - timedelta(seconds=65),
        completed_at=datetime.utcnow(),
        duration_seconds=65,
        head_commit=CommitInfo(
            sha="mno345",
            author="testuser",
            message="ci: add resource validation step",
            timestamp=datetime.utcnow(),
            files_changed=[".github/workflows/ci.yml"],
        ),
        logs=[
            LogLine(step="Simulate resource exhaustion", level="info",
                    message="timeout 5 bash -c 'while true; do :; done'"),
            LogLine(step="Simulate resource exhaustion", level="error",
                    message="timed out after 5 seconds"),
            LogLine(step="Simulate resource exhaustion", level="error",
                    message="Process completed with exit code 124"),
        ],
        diff_hunks=[
            DiffHunk(
                file_path=".github/workflows/ci.yml",
                old_lines=[],
                new_lines=[
                    "      - name: Simulate resource exhaustion",
                    "        run: |",
                    "          timeout 5 bash -c 'while true; do :; done'",
                    "          exit 124",
                ],
                change_type="added",
            )
        ],
        raw_payload={},
    )


async def seed_failures() -> None:
    """Process all 5 synthetic failure fixtures through the RCA pipeline and persist them."""
    import asyncio
    from app.llm.orchestrator import RCAOrchestrator
    orchestrator = RCAOrchestrator()
    contexts = [
        synthetic_dependency_failure(),
        synthetic_syntax_error_failure(),
        synthetic_test_assertion_failure(),
        synthetic_config_drift_failure(),
        synthetic_resource_exhaustion_failure(),
    ]
    for i, ctx in enumerate(contexts):
        try:
            await orchestrator.process(ctx)
            print(f"[seed] Processed {ctx.id} ({i+1}/{len(contexts)})")
        except Exception as e:
            print(f"[seed] Failed {ctx.id}: {e}")
        if i < len(contexts) - 1:
            await asyncio.sleep(15)  # Respect Gemini free-tier RPM limit
