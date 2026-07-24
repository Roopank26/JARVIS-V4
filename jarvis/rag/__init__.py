"""
RAG (Retrieval Augmented Generation) module for JARVIS.
"""

from jarvis.rag.citations import Citation, CitationFormatter, CitationResult
from jarvis.rag.document_processor import (
    DocumentChunk,
    DocumentProcessor,
    ProcessedDocument,
    StudyAssistant,
)
from jarvis.rag.hybrid_search import HybridSearchEngine
from jarvis.rag.rag_system import RAGSystem, get_rag_system, init_rag_system

__all__ = [
    # Document processing
    "DocumentProcessor",
    "DocumentChunk",
    "ProcessedDocument",
    "StudyAssistant",
    # Hybrid search
    "HybridSearchEngine",
    # Citations
    "CitationFormatter",
    "Citation",
    "CitationResult",
    # RAG system
    "RAGSystem",
    "get_rag_system",
    "init_rag_system",
]
