# app/graph/store.py
from abc import ABC, abstractmethod
import networkx as nx

class GraphStore(ABC):
    @abstractmethod
    def save(self, failure_id: str, graph: nx.DiGraph) -> None: ...

    @abstractmethod
    def load(self, failure_id: str) -> nx.DiGraph | None: ...

class NetworkXStore(GraphStore):
    """In-memory store. Swap for Neo4jStore in production."""
    def __init__(self):
        self._store: dict[str, nx.DiGraph] = {}

    def save(self, failure_id: str, graph: nx.DiGraph) -> None:
        self._store[failure_id] = graph

    def load(self, failure_id: str) -> nx.DiGraph | None:
        return self._store.get(failure_id)
