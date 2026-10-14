"""Tenant-scoped precedent ingestion and hybrid retrieval for local MongoDB."""

import hashlib
import math
from datetime import datetime
from uuid import UUID, uuid4

from pymongo import MongoClient

from app.config.settings import settings
from app.services.embedding_service import embedding_service


class MongoRagService:
    def __init__(self):
        if not settings.MONGODB_URL:
            raise RuntimeError("MONGODB_URL is not configured.")
        self.client = MongoClient(settings.MONGODB_URL, serverSelectionTimeoutMS=3000)
        database = self.client[settings.MONGODB_DATABASE]
        self.documents = database["precedent_documents"]
        self.chunks = database["precedent_chunks"]

    @staticmethod
    def _chunk_text(content: str, size: int = 1400, overlap: int = 180):
        words = content.split()
        chunks = []
        start = 0
        while start < len(words):
            end = min(start + size, len(words))
            chunks.append(" ".join(words[start:end]))
            if end == len(words):
                break
            start = end - overlap
        return chunks

    @staticmethod
    def _cosine(left: list[float], right: list[float]) -> float:
        numerator = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        if not left_norm or not right_norm:
            return 0.0
        return numerator / (left_norm * right_norm)

    def _embed(self, text: str) -> list[float]:
        return embedding_service.generate_embedding(text)

    def ingest(self, *, organization_id: UUID, payload) -> dict:
        content_hash = hashlib.sha256(payload.content.encode("utf-8")).hexdigest()
        existing = self.documents.find_one(
            {"organization_id": str(organization_id), "content_hash": content_hash}
        )
        if existing:
            return {"document_id": existing["_id"], "status": "already_exists"}

        document_id = str(uuid4())
        document = {
            "_id": document_id,
            "organization_id": str(organization_id),
            "title": payload.title,
            "citation": payload.citation,
            "court": payload.court,
            "case_type": payload.case_type,
            "decision_year": payload.decision_year,
            "source_uri": payload.source_uri,
            "content_hash": content_hash,
            "created_at": datetime.utcnow(),
        }
        chunks = []
        for index, text in enumerate(self._chunk_text(payload.content)):
            chunks.append(
                {
                    "_id": str(uuid4()),
                    "organization_id": str(organization_id),
                    "document_id": document_id,
                    "chunk_index": index,
                    "content": text,
                    "embedding": self._embed(text),
                }
            )
        self.documents.insert_one(document)
        if chunks:
            self.chunks.insert_many(chunks)
        return {
            "document_id": document_id,
            "status": "created",
            "chunk_count": len(chunks),
        }

    def search(self, *, organization_id: UUID, payload) -> list[dict]:
        query_embedding = self._embed(payload.query)
        query_terms = {term.lower() for term in payload.query.split() if len(term) > 2}
        document_filter = {
            "organization_id": str(organization_id),
            **({"case_type": payload.case_type} if payload.case_type else {}),
        }
        documents = {
            item["_id"]: item
            for item in self.documents.find(document_filter)
        }
        scored = []
        mismatched_dimensions = 0
        for chunk in self.chunks.find(
            {"organization_id": str(organization_id), "document_id": {"$in": list(documents)}}
        ):
            if len(chunk.get("embedding", [])) != len(query_embedding):
                mismatched_dimensions += 1
                continue
            document = documents[chunk["document_id"]]
            content_terms = set(chunk["content"].lower().split())
            keyword_score = len(query_terms & content_terms) / max(len(query_terms), 1)
            vector_score = self._cosine(query_embedding, chunk["embedding"])
            score = 0.65 * vector_score + 0.35 * keyword_score
            scored.append(
                {
                    "document_id": document["_id"],
                    "title": document["title"],
                    "citation": document.get("citation"),
                    "court": document.get("court"),
                    "decision_year": document.get("decision_year"),
                    "chunk_index": chunk["chunk_index"],
                    "content": chunk["content"],
                    "vector_score": round(vector_score, 6),
                    "keyword_score": round(keyword_score, 6),
                    "relevance_score": round(score, 6),
                }
            )
        if mismatched_dimensions:
            raise RuntimeError(
                "Stored precedent embeddings use a different vector dimension. "
                "Re-index those documents before searching with the selected embedding provider."
            )
        scored.sort(key=lambda item: item["relevance_score"], reverse=True)
        return scored[: payload.limit]

    def reindex_document(self, *, organization_id: UUID, document_id: str) -> dict:
        document = self.documents.find_one(
            {"_id": document_id, "organization_id": str(organization_id)}
        )
        if not document:
            raise KeyError("Precedent document was not found.")
        chunks = list(
            self.chunks.find(
                {"document_id": document_id, "organization_id": str(organization_id)}
            )
        )
        dimension = 0
        for chunk in chunks:
            embedding = self._embed(chunk["content"])
            dimension = len(embedding)
            self.chunks.update_one(
                {"_id": chunk["_id"]},
                {"$set": {"embedding": embedding}},
            )
        return {
            "document_id": document_id,
            "status": "reindexed",
            "chunk_count": len(chunks),
            "embedding_dimension": dimension,
        }
