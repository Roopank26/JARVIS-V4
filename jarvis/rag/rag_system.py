"""
RAG System for JARVIS - Retrieval Augmented Generation with local knowledge base.
Enhanced with hybrid search and citation tracking.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from jarvis.memory.knowledge import LocalKnowledgeBase
from jarvis.rag.citations import Citation, CitationFormatter, CitationResult
from jarvis.rag.document_processor import DocumentProcessor, StudyAssistant
from jarvis.rag.hybrid_search import HybridSearchEngine

logger = logging.getLogger(__name__)


class RAGSystem:
    """
    RAG (Retrieval Augmented Generation) system for JARVIS.

    Capabilities:
    - Document ingestion (PDF, TXT, MD, DOCX)
    - Semantic search using vector embeddings
    - Hybrid search with BM25 + vector search + reranking
    - Context retrieval for answering questions
    - Study assistance (summaries, questions, notes)
    - Citation tracking and formatting
    """

    def __init__(
        self, storage_path: Path | None = None, chunk_size: int = 500, chunk_overlap: int = 50
    ):
        self.storage_path = storage_path or Path.home() / ".jarvis" / "knowledge"
        self.processor = DocumentProcessor(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.study_assistant = StudyAssistant(self.processor)
        self.knowledge_base = LocalKnowledgeBase(self.storage_path)
        self._initialized = False
        self._document_index: dict[str, dict] = {}
        self._hybrid_search: HybridSearchEngine | None = None
        self._citation_formatter = CitationFormatter()
        self._citation_map: dict[str, dict[str, Any]] = {}

    def close(self) -> None:
        """Release resources held by the RAG system."""
        try:
            if self.knowledge_base is not None:
                self.knowledge_base.close()
        except Exception:
            pass

        try:
            if self._hybrid_search is not None and hasattr(self._hybrid_search, "vector_backend"):
                backend = self._hybrid_search.vector_backend
                if hasattr(backend, "_chromadb") and backend._chromadb is not None:
                    backend._chromadb.close()
        except Exception:
            pass

    async def initialize(self) -> bool:
        """Initialize the RAG system."""
        if self._initialized:
            return True

        await self.knowledge_base.initialize()

        self._hybrid_search = HybridSearchEngine(self.storage_path)
        self._hybrid_search.initialize()

        self._load_document_index()
        self._initialized = True
        return True

    def _get_index_path(self) -> Path:
        """Get the document index file path."""
        return self.storage_path / "document_index.json"

    def _load_document_index(self) -> None:
        """Load document index from disk."""
        index_path = self._get_index_path()
        if index_path.exists():
            try:
                with open(index_path) as f:
                    self._document_index = json.load(f)
                logger.info(f"Loaded document index with {len(self._document_index)} documents")
            except Exception as e:
                logger.warning(f"Failed to load document index: {e}")
                self._document_index = {}

    def _save_document_index(self) -> None:
        """Save document index to disk."""
        index_path = self._get_index_path()
        index_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(index_path, "w") as f:
                json.dump(self._document_index, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save document index: {e}")

    async def ingest_document(
        self, file_path: Path, tags: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Ingest a document into the knowledge base.

        Args:
            file_path: Path to the document
            tags: Optional tags for categorization

        Returns:
            Dictionary with ingestion stats
        """
        await self.initialize()

        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")

        # Process document
        doc = await self.processor.process_file(file_path)

        # Add chunks to knowledge base and hybrid search
        added_count = 0
        hybrid_entries: list[tuple[str, str, dict]] = []

        for chunk in doc.chunks:
            entry_id = chunk.id

            citation_info = {
                "document_title": doc.title,
                "page": chunk.page,
                "chunk_index": chunk.chunk_index,
                "source_path": str(file_path),
            }
            self._citation_map[entry_id] = citation_info

            metadata = {
                **chunk.metadata,
                "document_title": doc.title,
                "chunk_index": chunk.chunk_index,
                "source_path": str(file_path),
            }

            hybrid_entries.append((entry_id, chunk.content, metadata))

            await self.knowledge_base.add(
                content=chunk.content,
                tags=tags or [doc.file_type, doc.title],
                metadata=metadata,
                source=str(file_path),
            )
            added_count += 1

        if self._hybrid_search is not None:
            try:
                self._hybrid_search.index_documents(hybrid_entries)
            except Exception as e:
                logger.warning(f"Hybrid search indexing failed: {e}")

        # Update document index
        doc_id = str(file_path.resolve())
        self._document_index[doc_id] = {
            "title": doc.title,
            "source": str(file_path),
            "file_type": doc.file_type,
            "chunk_count": len(doc.chunks),
            "ingested_at": datetime.now().isoformat(),
            "tags": tags or [],
        }
        self._save_document_index()

        return {
            "success": True,
            "title": doc.title,
            "chunks_added": added_count,
            "total_chunks": len(doc.chunks),
        }

    async def search(self, query: str, limit: int = 5, tags: list[str] | None = None) -> list[dict]:
        """
        Search the knowledge base for relevant content.

        Args:
            query: Search query
            limit: Maximum results
            tags: Filter by tags

        Returns:
            List of relevant chunks
        """
        await self.initialize()

        if self._hybrid_search is not None:
            try:
                hybrid_results = self._hybrid_search.search(query, limit=limit, tags=tags)
                if hybrid_results:
                    formatted: list[dict] = []
                    for r in hybrid_results:
                        formatted.append(
                            {
                                "id": r.id,
                                "content": r.content,
                                "score": r.score,
                                "metadata": r.metadata,
                            }
                        )
                    return formatted
            except Exception as e:
                logger.warning(f"Hybrid search failed, falling back to knowledge_base.search: {e}")

        return await self.knowledge_base.search(query, limit=limit, tags=tags)

    async def hybrid_search(
        self, query: str, limit: int = 5, tags: list[str] | None = None
    ) -> list[dict]:
        """
        Search using the hybrid search engine.

        Args:
            query: Search query
            limit: Maximum results
            tags: Filter by tags

        Returns:
            List of relevant chunks with hybrid scores
        """
        await self.initialize()

        if self._hybrid_search is None:
            raise RuntimeError("Hybrid search engine not initialized")

        results = self._hybrid_search.search(query, limit=limit, tags=tags)
        formatted: list[dict] = []
        for r in results:
            formatted.append(
                {
                    "id": r.id,
                    "content": r.content,
                    "score": r.score,
                    "bm25_score": r.bm25_score,
                    "vector_score": r.vector_score,
                    "rerank_score": r.rerank_score,
                    "metadata": r.metadata,
                }
            )
        return formatted

    def get_citations(self, results: list[dict]) -> str:
        """
        Get formatted citations for search results.

        Args:
            results: List of search results from search()

        Returns:
            Formatted citation string
        """
        citation_results: list[CitationResult] = []

        for r in results:
            r_id = r.get("id", "")
            meta = r.get("metadata", {})
            citation_info = self._citation_map.get(r_id, {})

            source_path = citation_info.get("source_path", meta.get("source_path", meta.get("source", "Unknown")))
            document_title = citation_info.get("document_title", meta.get("document_title", meta.get("file_name", "Unknown")))
            page = citation_info.get("page", meta.get("page"))
            chunk_index = citation_info.get("chunk_index", meta.get("chunk_index", 0))

            citation = Citation(
                source_path=source_path,
                document_title=document_title,
                page=page,
                chunk_index=chunk_index,
                score=r.get("score", 0.0),
                metadata=meta,
            )
            citation_results.append(
                CitationResult(
                    content=r.get("content", ""),
                    citation=citation,
                    score=r.get("score", 0.0),
                )
            )

        return self._citation_formatter.inline(citation_results)

    def get_citations_detailed(self, results: list[dict]) -> list[CitationResult]:
        """
        Get citation objects for search results.

        Args:
            results: List of search results from search()

        Returns:
            List of CitationResult objects
        """
        citation_results: list[CitationResult] = []

        for r in results:
            r_id = r.get("id", "")
            meta = r.get("metadata", {})
            citation_info = self._citation_map.get(r_id, {})

            source_path = citation_info.get("source_path", meta.get("source_path", meta.get("source", "Unknown")))
            document_title = citation_info.get("document_title", meta.get("document_title", meta.get("file_name", "Unknown")))
            page = citation_info.get("page", meta.get("page"))
            chunk_index = citation_info.get("chunk_index", meta.get("chunk_index", 0))

            citation = Citation(
                source_path=source_path,
                document_title=document_title,
                page=page,
                chunk_index=chunk_index,
                score=r.get("score", 0.0),
                metadata=meta,
            )
            citation_results.append(
                CitationResult(
                    content=r.get("content", ""),
                    citation=citation,
                    score=r.get("score", 0.0),
                )
            )

        return citation_results

    async def get_context(self, query: str, max_chunks: int = 5) -> str:
        """
        Get relevant context for a query.

        Args:
            query: Search query
            max_chunks: Maximum chunks to retrieve

        Returns:
            Combined context string
        """
        results = await self.search(query, limit=max_chunks)

        if not results:
            return ""

        citations = self.get_citations(results)

        context_parts = []
        for i, result in enumerate(results, 1):
            content = result.get("content", "")
            context_parts.append(f"[Source {i}]\n{content}")

        combined = "\n\n".join(context_parts)
        if citations:
            combined += f"\n\n{citations}"
        return combined

    async def list_documents(self) -> list[dict[str, Any]]:
        """List all ingested documents."""
        await self.initialize()

        docs = []
        for doc_id, info in self._document_index.items():
            docs.append(
                {
                    "id": doc_id,
                    "title": info.get("title", "Untitled"),
                    "file_type": info.get("file_type", "unknown"),
                    "chunk_count": info.get("chunk_count", 0),
                    "ingested_at": info.get("ingested_at", ""),
                    "tags": info.get("tags", []),
                }
            )

        return sorted(docs, key=lambda x: x.get("ingested_at", ""), reverse=True)

    async def delete_document(self, file_path: Path) -> bool:
        """Delete a document from the knowledge base."""
        await self.initialize()

        doc_id = str(Path(file_path).resolve())

        if doc_id not in self._document_index:
            return False

        # Remove from index
        del self._document_index[doc_id]
        self._save_document_index()

        logger.info(f"Removed document from index: {file_path}")
        return True

    async def summarize(self, file_path: Path, max_length: int = 500) -> str:
        """Generate a summary of a document."""
        return await self.study_assistant.summarize_document(file_path, max_length)

    async def generate_questions(self, file_path: Path, num_questions: int = 5) -> list[str]:
        """Generate practice questions from a document."""
        return await self.study_assistant.generate_questions(file_path, num_questions)

    async def generate_notes(self, file_path: Path, format_type: str = "bullet") -> str:
        """Generate revision notes from a document."""
        return await self.study_assistant.generate_exam_notes(file_path, format_type)

    def get_stats(self) -> dict[str, Any]:
        """Get RAG system statistics."""
        kb_stats = self.knowledge_base.get_stats()
        hybrid_stats: dict[str, Any] = {}
        if self._hybrid_search is not None:
            hybrid_stats = {
                "hybrid_search_available": True,
                "bm25_docs": self._hybrid_search.bm25.count(),
                "vector_search_available": self._hybrid_search.vector_backend.is_available(),
            }
        else:
            hybrid_stats = {"hybrid_search_available": False}

        return {
            **kb_stats,
            **hybrid_stats,
            "documents_indexed": len(self._document_index),
            "storage_path": str(self.storage_path),
        }


# Global RAG system instance
_rag_system: RAGSystem | None = None


def get_rag_system() -> RAGSystem:
    """Get the global RAG system instance."""
    global _rag_system
    if _rag_system is None:
        _rag_system = RAGSystem()
    return _rag_system


def init_rag_system(storage_path: Path | None = None) -> RAGSystem:
    """Initialize the global RAG system."""
    global _rag_system
    _rag_system = RAGSystem(storage_path)
    return _rag_system
