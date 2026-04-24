# app/detection/centrality.py
import networkx as nx

class CentralityRanker:
    def rank(self, graph: nx.DiGraph) -> list[tuple[str, float]]:
        """Return nodes ranked by betweenness centrality, highest first."""
        if graph.number_of_nodes() == 0:
            return []
        undirected = graph.to_undirected()
        scores = nx.betweenness_centrality(undirected)
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)
