"""
Hybrid Search Engine for JARVIS RAG System.

Combines BM25/lexical search with semantic vector search,
and applies cross-encoder reranking for best-of-both retrieval.

Design principles:
- Backward compatible — runs alongside existing TF-IDF + ChromaDB
- Lazy-loads heavy dependencies (sentence-transformers, cross-encoder)
- Gracefully degrades to BM25-only when embeddings unavailable
- Maintains deterministic unit testability
"""

from __future__ import annotations

import contextlib
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Unified search result from hybrid retrieval."""

    id: str
    content: str
    score: float
    bm25_score: float = 0.0
    vector_score: float = 0.0
    rerank_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    source: str = ""
    citations: list[str] = field(default_factory=list)


class BM25Store:
    """
    BM25 (Best Matching 25) lexical search over a local snapshot.

    Stateless index rebuilt from entry payloads. Suitable for small-to-medium
    corpora and deterministic offline search.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self._doc_lengths: dict[str, int] = {}
        self._avg_doc_length: float = 0.0
        self._inverted_index: dict[str, dict[str, int]] = {}
        self._documents: dict[str, dict] = {}
        self._doc_count: int = 0

    def _tokenize(self, text: str) -> list[str]:
        text = text.lower()
        tokens = [t for t in __import__("re").findall(r"\b\w+\b", text) if len(t) > 2]
        return tokens

    def build(self, entries: list[tuple[str, str, dict]]) -> None:
        self._documents = {}
        self._inverted_index = {}
        self._doc_lengths = {}
        self._doc_count = len(entries)

        for entry_id, content, metadata in entries:
            tokens = self._tokenize(content)
            self._documents[entry_id] = {
                "content": content,
                "metadata": metadata,
                "tokens": tokens,
            }
            self._doc_lengths[entry_id] = len(tokens)
            for token in tokens:
                if token not in self._inverted_index:
                    self._inverted_index[token] = {}
                self._inverted_index[token][entry_id] = (
                    self._inverted_index[token].get(entry_id, 0) + 1
                )

        if self._doc_lengths:
            self._avg_doc_length = sum(self._doc_lengths.values()) / len(self._doc_lengths)
        else:
            self._avg_doc_length = 0.0

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        if not self._documents or not query:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scores: dict[str, float] = {}
        for token in query_tokens:
            postings = self._inverted_index.get(token, {})
            doc_freq = len(postings)
            if doc_freq == 0:
                continue
            idf = math.log(1 + (self._doc_count - doc_freq + 0.5) / (doc_freq + 0.5))
            for doc_id, freq in postings.items():
                dl = self._doc_lengths.get(doc_id, 1) or 1
                numerator = freq * (self.k1 + 1)
                denominator = freq + self.k1 * (1 - self.b + self.b * (dl / (self._avg_doc_length or 1)))
                scores[doc_id] = scores.get(doc_id, 0.0) + idf * numerator / denominator

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]
        results = []
        for doc_id, score in ranked:
            doc = self._documents.get(doc_id, {})
            results.append(
                SearchResult(
                    id=doc_id,
                    content=doc.get("content", ""),
                    score=score,
                    bm25_score=score,
                    metadata=doc.get("metadata", {}),
                )
            )
        return results

    def count(self) -> int:
        return self._doc_count


class VectorSearchBackend:
    """
    Thin wrapper around ChromaDB or in-memory embeddings.

    Uses sentence-transformers for embeddings. Falls back to a simple
    TF-IDF cosine fallback when ChromaDB is unavailable.
    """

    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path
        self._chromadb = None
        self._embedding_model = None
        self._collection = None
        self._available = False
        self._metadata: dict[str, dict] = {}

    def initialize(self) -> bool:
        try:
            import chromadb
            from chromadb.config import Settings

            self._chromadb = chromadb.PersistentClient(
                path=str(self.storage_path / "chroma_db"),
                settings=Settings(anonymized_telemetry=False),
            )
            self._collection = self._chromadb.get_or_create_collection(
                name="jarvis_hybrid_knowledge", metadata={"hnsw:space": "cosine"}
            )
            self._available = True
            logger.info("Vector search initialized with ChromaDB")
            return True
        except Exception as exc:
            logger.info(f"Vector search fallback mode: {exc}")
            return False

    def _ensure_model(self) -> None:
        if self._embedding_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception as exc:
                logger.debug(f"sentence-transformers unavailable: {exc}")
                self._embedding_model = None

    def add(self, entry_id: str, content: str, metadata: dict) -> None:
        self._metadata[entry_id] = metadata
        if not self._available:
            return
        try:
            self._ensure_model()
            if self._embedding_model is None:
                return
            embedding = self._embedding_model.encode([content], normalize_embeddings=True)[0]
            self._collection.upsert(
                ids=[entry_id],
                documents=[content],
                embeddings=[embedding.tolist()],
                metadatas=[metadata],
            )
        except Exception as exc:
            logger.debug(f"Vector add failed: {exc}")

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        if not self._available:
            return []

        try:
            self._ensure_model()
            if self._embedding_model is None:
                return []

            query_embedding = self._embedding_model.encode([query], normalize_embeddings=True)[0]
            results = self._collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=limit,
            )
            output = []
            docs = results.get("documents", [[]])[0]
            ids = results.get("ids", [[]])[0]
            distances = results.get("distances", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            for i, doc in enumerate(docs):
                entry_id = ids[i] if i < len(ids) else ""
                distance = distances[i] if i < len(distances) else 0.0
                meta = metas[i] if i < len(metas) else {}
                output.append(
                    SearchResult(
                        id=entry_id,
                        content=doc,
                        score=max(0.0, 1.0 - distance),
                        vector_score=max(0.0, 1.0 - distance),
                        metadata=meta or {},
                    )
                )
            return output
        except Exception as exc:
            logger.debug(f"Vector search failed: {exc}")
            return []

    def is_available(self) -> bool:
        return self._available


class HybridSearchEngine:
    """
    Combines BM25 and vector search with optional reranking.

    Features:
    - Reciprocal Rank Fusion (RRF) for combining BM25 and vector lists
    - Cross-encoder reranking when model is available
    - Citation-aware result formatting
    """

    def __init__(self, storage_path: Path | None = None) -> None:
        self.storage_path = storage_path or Path.home() / ".jarvis" / "knowledge"
        self.bm25 = BM25Store()
        self.vector_backend = VectorSearchBackend(self.storage_path)
        self._reranker = None
        self._initialized = False

    def initialize(self) -> bool:
        if self._initialized:
            return True
        vector_ok = self.vector_backend.initialize()
        self._initialized = True
        if vector_ok:
            logger.info("HybridSearch: vector backend ready")
        else:
            logger.info("HybridSearch: BM25-only mode")
        return True

    def _lazy_reranker(self):
        if self._reranker is None:
            try:
                from sentence_transformers import CrossEncoder
                self._reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            except Exception as exc:
                logger.debug(f"Cross-encoder reranker unavailable: {exc}")
                self._reranker = False
        if self._reranker is False:
            return None
        return self._reranker

    def index_documents(self, entries: list[tuple[str, str, dict]]) -> None:
        self.bm25.build(entries)
        for entry_id, content, metadata in entries:
            with contextlib.suppress(Exception):
                self.vector_backend.add(entry_id, content, metadata)

    def _reciprocal_rank_fusion(
        self, bm25_results: list[SearchResult], vector_results: list[SearchResult], k: int = 60
    ) -> list[SearchResult]:
        rrf_scores: dict[str, float] = {}
        result_map: dict[str, SearchResult] = {}

        for rank, result in enumerate(bm25_results, start=1):
            rrf_scores[result.id] = rrf_scores.get(result.id, 0.0) + 1.0 / (k + rank)
            result_map[result.id] = result

        for rank, result in enumerate(vector_results, start=1):
            rrf_scores[result.id] = rrf_scores.get(result.id, 0.0) + 1.0 / (k + rank)
            if result.id not in result_map or rank == 0:
                result_map[result.id] = result

        merged = []
        for doc_id, rrf_score in sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True):
            result = result_map.get(doc_id)
            if result:
                result.score = rrf_score
                merged.append(result)
        return merged

    def search(
        self,
        query: str,
        limit: int = 5,
        rerank: bool = True,
        tags: list[str] | None = None,
    ) -> list[SearchResult]:
        if not query:
            return []

        bm25_k = limit * 2
        v_k = limit * 2

        bm25_results = self.bm25.search(query, bm25_k)
        vector_results = self.vector_backend.search(query, v_k)

        if tags:
            bm25_results = [r for r in bm25_results if any(t in r.metadata.get("tags", []) for t in tags)]
            vector_results = [r for r in vector_results if any(t in r.metadata.get("tags", []) for t in tags)]

        if not bm25_results and not vector_results:
            return []

        merged = self._reciprocal_rank_fusion(bm25_results, vector_results)

        if rerank:
            reranker = self._lazy_reranker()
            if reranker and len(merged) > 1:
                try:
                    pairs = [(query, r.content) for r in merged]
                    rerank_scores = reranker.predict(pairs)
                    for result, rerank_score in zip(merged, rerank_scores, strict=False):
                        result.rerank_score = float(rerank_score)
                        result.score = 0.3 * result.score + 0.7 * result.rerank_score
                    merged.sort(key=lambda r: r.score, reverse=True)
                except Exception as exc:
                    logger.debug(f"Reranking failed: {exc}")

        return merged[:limit]
