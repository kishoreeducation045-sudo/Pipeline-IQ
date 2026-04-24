# app/graph/builder.py
import networkx as nx
from app.models.failure import FailureContext

class FailureGraph:
    def __init__(self):
        self.graph = nx.DiGraph()

    def build(self, ctx: FailureContext) -> nx.DiGraph:
        g = nx.DiGraph()
        commit = ctx.head_commit

        # Commit node
        g.add_node(f"commit:{commit.sha}",
                   type="Commit",
                   sha=commit.sha,
                   author=commit.author,
                   message=commit.message)

        # File nodes + MODIFIES edges
        for file_path in commit.files_changed:
            file_id = f"file:{file_path}"
            g.add_node(file_id, type="File", path=file_path)
            g.add_edge(f"commit:{commit.sha}", file_id, type="MODIFIES")

            # Detect dependency file changes (INTRODUCES dep)
            if file_path in ("requirements.txt", "package.json", "Cargo.toml", "pyproject.toml"):
                for hunk in ctx.diff_hunks:
                    if hunk.file_path == file_path:
                        for line in hunk.new_lines:
                            dep = self._parse_dep(line, file_path)
                            if dep:
                                dep_id = f"dep:{dep['name']}@{dep['version']}"
                                g.add_node(dep_id, type="Dependency", **dep)
                                g.add_edge(f"commit:{commit.sha}", dep_id, type="INTRODUCES")

        # PipelineStep nodes (derive from logs)
        steps = {line.step for line in ctx.logs}
        for step in steps:
            step_id = f"step:{step}"
            error_lines = [l for l in ctx.logs if l.step == step and l.level == "error"]
            status = "failed" if error_lines else "passed"
            g.add_node(step_id, type="PipelineStep", name=step, status=status)
            g.add_edge(f"commit:{commit.sha}", step_id, type="TRIGGERS")

        # Test nodes + FAILS_IN edges
        for test in ctx.test_results:
            test_id = f"test:{test.name}"
            g.add_node(test_id, type="Test", name=test.name, passed=test.passed,
                       failure_message=test.failure_message)
            if not test.passed:
                # Assume tests ran in a "test" step; refine with actual step mapping
                failing_steps = [n for n, d in g.nodes(data=True)
                                 if d.get("type") == "PipelineStep" and d.get("status") == "failed"]
                for step_id in failing_steps:
                    g.add_edge(test_id, step_id, type="FAILS_IN")

        self.graph = g
        return g

    @staticmethod
    def _parse_dep(line: str, filename: str) -> dict | None:
        """Very simple parser — good enough for prototype."""
        line = line.strip()
        if filename == "requirements.txt" and "==" in line:
            name, _, version = line.partition("==")
            return {"name": name.strip(), "version": version.strip(), "ecosystem": "pip"}
        # Add npm/cargo parsing as needed
        return None
