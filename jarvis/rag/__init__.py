"""
RAG (Retrieval Augmented Generation) module for JARVIS.
"""

from jarvis.rag.document_processor import (
    DocumentChunk,
    DocumentProcessor,
    ProcessedDocument,
    StudyAssistant,
)
from jarvis.rag.rag_system import RAGSystem, get_rag_system, init_rag_system

__all__ = [
    # Document processing
    "DocumentProcessor",
    "DocumentChunk",
    "ProcessedDocument",
    "StudyAssistant",
    # RAG system
    "RAGSystem",
    "get_rag_system",
    "init_rag_system",
]
