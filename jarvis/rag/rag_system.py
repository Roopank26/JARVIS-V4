"""
RAG System for JARVIS - Retrieval Augmented Generation with local knowledge base.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime

from jarvis.rag.document_processor import DocumentProcessor, ProcessedDocument, StudyAssistant
from jarvis.memory.knowledge import LocalKnowledgeBase

logger = logging.getLogger(__name__)


class RAGSystem:
    """
    RAG (Retrieval Augmented Generation) system for JARVIS.
    
    Capabilities:
    - Document ingestion (PDF, TXT, MD, DOCX)
    - Semantic search using vector embeddings
    - Context retrieval for answering questions
    - Study assistance (summaries, questions, notes)
    """

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ):
        self.storage_path = storage_path or Path.home() / ".jarvis" / "knowledge"
        self.processor = DocumentProcessor(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.study_assistant = StudyAssistant(self.processor)
        self.knowledge_base = LocalKnowledgeBase(self.storage_path)
        self._initialized = False
        self._document_index: Dict[str, Dict] = {}

    async def initialize(self) -> bool:
        """Initialize the RAG system."""
        if self._initialized:
            return True
        
        await self.knowledge_base.initialize()
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
                with open(index_path, 'r') as f:
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
            with open(index_path, 'w') as f:
                json.dump(self._document_index, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save document index: {e}")

    async def ingest_document(self, file_path: Path, tags: Optional[List[str]] = None) -> Dict[str, Any]:
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
        
        # Add chunks to knowledge base
        added_count = 0
        for chunk in doc.chunks:
            await self.knowledge_base.add(
                content=chunk.content,
                tags=tags or [doc.file_type, doc.title],
                metadata={
                    **chunk.metadata,
                    "document_title": doc.title,
                    "chunk_index": chunk.chunk_index
                },
                source=str(file_path)
            )
            added_count += 1
        
        # Update document index
        doc_id = str(file_path.resolve())
        self._document_index[doc_id] = {
            "title": doc.title,
            "source": str(file_path),
            "file_type": doc.file_type,
            "chunk_count": len(doc.chunks),
            "ingested_at": datetime.now().isoformat(),
            "tags": tags or []
        }
        self._save_document_index()
        
        return {
            "success": True,
            "title": doc.title,
            "chunks_added": added_count,
            "total_chunks": len(doc.chunks)
        }

    async def search(self, query: str, limit: int = 5, tags: Optional[List[str]] = None) -> List[Dict]:
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
        return await self.knowledge_base.search(query, limit=limit, tags=tags)

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
        
        context_parts = []
        for i, result in enumerate(results, 1):
            content = result.get('content', '')
            source = result.get('metadata', {}).get('file_name', 'Unknown')
            context_parts.append(f"[Source {i}: {source}]\n{content}")
        
        return "\n\n".join(context_parts)

    async def list_documents(self) -> List[Dict[str, Any]]:
        """List all ingested documents."""
        await self.initialize()
        
        docs = []
        for doc_id, info in self._document_index.items():
            docs.append({
                "id": doc_id,
                "title": info.get("title", "Untitled"),
                "file_type": info.get("file_type", "unknown"),
                "chunk_count": info.get("chunk_count", 0),
                "ingested_at": info.get("ingested_at", ""),
                "tags": info.get("tags", [])
            })
        
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
        
        # Note: We'd need to track chunk IDs to delete them from knowledge base
        # For now, we just remove from the index
        logger.info(f"Removed document from index: {file_path}")
        return True

    async def summarize(self, file_path: Path, max_length: int = 500) -> str:
        """Generate a summary of a document."""
        return await self.study_assistant.summarize_document(file_path, max_length)

    async def generate_questions(self, file_path: Path, num_questions: int = 5) -> List[str]:
        """Generate practice questions from a document."""
        return await self.study_assistant.generate_questions(file_path, num_questions)

    async def generate_notes(self, file_path: Path, format_type: str = "bullet") -> str:
        """Generate revision notes from a document."""
        return await self.study_assistant.generate_exam_notes(file_path, format_type)

    def get_stats(self) -> Dict[str, Any]:
        """Get RAG system statistics."""
        kb_stats = self.knowledge_base.get_stats()
        return {
            **kb_stats,
            "documents_indexed": len(self._document_index),
            "storage_path": str(self.storage_path)
        }


# Global RAG system instance
_rag_system: Optional[RAGSystem] = None


def get_rag_system() -> RAGSystem:
    """Get the global RAG system instance."""
    global _rag_system
    if _rag_system is None:
        _rag_system = RAGSystem()
    return _rag_system


def init_rag_system(storage_path: Optional[Path] = None) -> RAGSystem:
    """Initialize the global RAG system."""
    global _rag_system
    _rag_system = RAGSystem(storage_path)
    return _rag_system
