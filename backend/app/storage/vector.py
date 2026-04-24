# app/storage/vector.py
import chromadb
from chromadb.config import Settings
from app.config import settings

class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=settings.chroma_path,
            settings=Settings(anonymized_telemetry=False),
        )
        # One collection for failure summaries; embeddings via default model
        self.collection = self.client.get_or_create_collection(
            name="failure_summaries",
            metadata={"description": "Past RCA summaries for similarity retrieval"},
        )

    def add(self, failure_id: str, summary_text: str, metadata: dict):
        self.collection.add(
            ids=[failure_id],
            documents=[summary_text],
            metadatas=[metadata],
        )

    def similar(self, query_text: str, k: int = 3) -> list[dict]:
        if self.collection.count() == 0:
            return []
        res = self.collection.query(query_texts=[query_text], n_results=min(k, self.collection.count()))
        return [
            {"id": id_, "document": doc, "metadata": meta, "distance": dist}
            for id_, doc, meta, dist in zip(
                res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0]
            )
        ]

vector_store = VectorStore()
