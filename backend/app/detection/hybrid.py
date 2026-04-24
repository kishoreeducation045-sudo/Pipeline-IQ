# app/detection/hybrid.py
from app.detection.centrality import CentralityRanker
from app.detection.rules import RuleDetector, Candidate
from app.graph.builder import FailureGraph
from app.models.failure import FailureContext

class HybridDetector:
    def __init__(self):
        self.rules = RuleDetector()
        self.graph_builder = FailureGraph()
        self.ranker = CentralityRanker()

    def detect(self, ctx: FailureContext, top_k: int = 5) -> list[Candidate]:
        # Layer 1: rule-based candidates
        candidates = self.rules.detect(ctx)

        # Layer 2: graph centrality weighting
        graph = self.graph_builder.build(ctx)
        scores = dict(self.ranker.rank(graph))

        # Reweight candidate priors by connecting them to graph nodes
        enriched = []
        for c in candidates:
            bonus = 0.0
            # If candidate mentions a file from diff, boost by centrality of that file node
            for loc in c.evidence_locations:
                if loc.startswith("diff:"):
                    file_path = loc.split(":", 1)[1]
                    node_id = f"file:{file_path}"
                    if node_id in scores:
                        bonus = max(bonus, scores[node_id] * 0.2)
            c.confidence_prior = min(1.0, c.confidence_prior + bonus)
            enriched.append(c)

        # Sort by final prior, take top-K
        enriched.sort(key=lambda x: x.confidence_prior, reverse=True)
        return enriched[:top_k]
