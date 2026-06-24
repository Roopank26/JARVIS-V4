"""
Integration tests for RAG system with real documents.
"""

import pytest
import asyncio
from pathlib import Path

from jarvis.rag.rag_system import RAGSystem
from jarvis.rag.document_processor import DocumentProcessor, StudyAssistant


class TestRAGIntegration:
    """Integration tests for RAG system."""

    @pytest.fixture
    def test_doc_path(self):
        """Path to test document."""
        return Path("/workspace/project/JARVIS/test_data/neural_networks.txt")

    @pytest.fixture
    def rag_system(self, tmp_path):
        """Create RAG system with temp storage."""
        return RAGSystem(storage_path=tmp_path)

    @pytest.mark.asyncio
    async def test_ingest_real_document(self, rag_system, test_doc_path):
        """Test ingesting a real document."""
        if not test_doc_path.exists():
            pytest.skip("Test document not found")

        await rag_system.initialize()
        result = await rag_system.ingest_document(test_doc_path)

        assert result["status"] == "success"
        assert result["chunks"] > 0
        assert result["title"] is not None
        print(f"  Ingested: {result['chunks']} chunks")

    @pytest.mark.asyncio
    async def test_search_document(self, rag_system, test_doc_path):
        """Test searching ingested documents."""
        if not test_doc_path.exists():
            pytest.skip("Test document not found")

        await rag_system.initialize()
        await rag_system.ingest_document(test_doc_path)

        # Search for neural network content
        results = await rag_system.search("neural networks", top_k=3)

        assert len(results) > 0
        assert "neural" in results[0]["content"].lower() or "network" in results[0]["content"].lower()
        print(f"  Found {len(results)} results")

    @pytest.mark.asyncio
    async def test_study_assistant(self, rag_system, test_doc_path):
        """Test study assistant features."""
        if not test_doc_path.exists():
            pytest.skip("Test document not found")

        await rag_system.initialize()
        await rag_system.ingest_document(test_doc_path)

        # Test summary
        summary = await rag_system.study("summarize this document")
        assert summary is not None
        assert len(summary) > 50
        print(f"  Summary: {summary[:100]}...")

        # Test questions
        questions = await rag_system.study("generate interview questions")
        assert questions is not None
        assert len(questions) > 0
        print(f"  Generated {len(questions)} questions")


class TestDocumentProcessing:
    """Test document processing features."""

    @pytest.fixture
    def processor(self):
        """Create document processor."""
        return DocumentProcessor(chunk_size=200, chunk_overlap=20)

    @pytest.fixture
    def test_doc_path(self):
        """Path to test document."""
        return Path("/workspace/project/JARVIS/test_data/neural_networks.txt")

    def test_process_markdown_file(self, processor, test_doc_path):
        """Test processing a markdown file."""
        if not test_doc_path.exists():
            pytest.skip("Test document not found")

        doc = processor.process_file(test_doc_path)

        assert doc.file_type == "md"
        assert doc.title is not None
        assert len(doc.chunks) > 0
        print(f"  Processed: {len(doc.chunks)} chunks")

    def test_study_assistant_summary(self, processor):
        """Test study assistant summary generation."""
        study = StudyAssistant(processor)

        test_text = """
        Neural networks are computing systems inspired by biological brains.
        They consist of layers of interconnected neurons.
        Deep learning uses multiple hidden layers.
        """

        summary = study.summarize_document(test_text)
        assert summary is not None
        assert len(summary) < len(test_text)
        print(f"  Summary: {summary}")

    def test_study_assistant_questions(self, processor):
        """Test question generation."""
        study = StudyAssistant(processor)

        test_text = """
        Neural networks have three main components: neurons, layers, and connections.
        The input layer receives data, hidden layers process it, and the output layer produces results.
        Training uses backpropagation and gradient descent.
        """

        questions = study.generate_questions(test_text, num_questions=3)
        assert len(questions) <= 3
        assert all("?" in q for q in questions)
        print(f"  Generated questions: {questions}")


class TestRAGCommands:
    """Test RAG command patterns."""

    def test_rag_patterns_exist(self):
        """Test that RAG patterns are defined."""
        from jarvis.core.agent import RAG_QUERY_PATTERNS
        assert len(RAG_QUERY_PATTERNS) > 0

    def test_rag_query_recognized(self):
        """Test RAG queries are recognized."""
        from jarvis.core.agent import classify_intent, Intent

        # These should NOT go to CHAT
        result = classify_intent("ask the knowledge base about neural networks")
        assert result != Intent.CHAT, "RAG query should be recognized"

    def test_classify_returns_valid_intent(self):
        """Test classify returns valid intent types."""
        from jarvis.core.agent import classify_intent, Intent

        inputs = [
            "search my documents for deep learning",
            "what does the knowledge base say",
            "summarize this PDF",
        ]

        # Valid intent values (strings)
        valid_intents = ["chat", "memory_recall", "memory_store", "profile_query",
                        "rag_query", "provider_query", "tool_execution", "voice_status"]

        for inp in inputs:
            intent = classify_intent(inp)
            # Should not crash and return a valid intent string
            assert isinstance(intent, str), f"Expected string, got {type(intent)}"
            assert intent in valid_intents, f"Invalid intent: {intent}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
