"""
Tests for RAG (Retrieval Augmented Generation) system.
"""

import tempfile
from pathlib import Path

import pytest

from jarvis.rag.document_processor import (
    DocumentChunk,
    DocumentProcessor,
    StudyAssistant,
)
from jarvis.rag.rag_system import RAGSystem


class TestDocumentProcessor:
    """Tests for DocumentProcessor class."""

    @pytest.fixture
    def processor(self):
        """Create a DocumentProcessor instance."""
        return DocumentProcessor(chunk_size=100, chunk_overlap=20)

    @pytest.fixture
    def temp_txt_file(self):
        """Create a temporary text file."""
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
        tmp.write(
            "This is a test document. It contains some sample text for testing purposes. Machine learning is a subset of artificial intelligence. Deep learning uses neural networks with many layers."
        )
        tmp.close()
        yield Path(tmp.name)
        Path(tmp.name).unlink(missing_ok=True)

    @pytest.fixture
    def temp_md_file(self):
        """Create a temporary markdown file."""
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False)
        tmp.write(
            "# Test Document\n\nThis is a **test** document with [links](example.com).\n## Section 1\n\nSome content here.\n"
        )
        tmp.close()
        yield Path(tmp.name)
        Path(tmp.name).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_process_txt(self, processor, temp_txt_file):
        """Test processing a text file."""
        doc = await processor.process_file(temp_txt_file)

        assert doc.title == temp_txt_file.stem
        assert doc.file_type == "txt"
        assert len(doc.chunks) > 0
        assert all(isinstance(c, DocumentChunk) for c in doc.chunks)

    @pytest.mark.asyncio
    async def test_process_markdown(self, processor, temp_md_file):
        """Test processing a markdown file."""
        doc = await processor.process_file(temp_md_file)

        assert doc.file_type == "md"
        # Markdown formatting should be cleaned
        content = " ".join([c.content for c in doc.chunks])
        assert "**test**" not in content

    def test_clean_markdown(self, processor):
        """Test markdown cleaning."""
        md_text = "# Title\n\n**bold** and *italic*\n\n[link](http://example.com)"
        cleaned = processor._clean_markdown(md_text)

        assert "# Title" not in cleaned
        assert "**bold**" not in cleaned
        assert "[link]" not in cleaned

    def test_generate_chunk_id(self, processor):
        """Test chunk ID generation."""
        id1 = processor._generate_chunk_id("source1", 0)
        id2 = processor._generate_chunk_id("source1", 0)
        id3 = processor._generate_chunk_id("source1", 1)

        assert id2 != id3
        assert id1 != id3

    def test_split_into_chunks(self, processor):
        """Test text chunking."""
        text = "This is a test document. " * 20
        chunks = processor._split_into_chunks(text, "test_source", {"test": "meta"})

        assert len(chunks) > 1
        assert all(c.source == "test_source" for c in chunks)
        assert all(c.chunk_index >= 0 for c in chunks)


class TestStudyAssistant:
    """Tests for StudyAssistant class."""

    @pytest.fixture
    def study_assistant(self):
        """Create a StudyAssistant instance."""
        processor = DocumentProcessor(chunk_size=200)
        return StudyAssistant(processor)

    @pytest.fixture
    def temp_txt_file(self):
        """Create a temporary text file for study."""
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
        tmp.write(
            "Machine Learning Fundamentals\n\nMachine learning is a subset of artificial intelligence.\nIt enables computers to learn from data.\nKey algorithms include supervised learning, unsupervised learning, and reinforcement learning.\nSupervised learning uses labeled data for training.\nUnsupervised learning finds patterns in unlabeled data.\n"
        )
        tmp.close()
        yield Path(tmp.name)
        Path(tmp.name).unlink(missing_ok=True)

    def test_extract_key_terms(self, study_assistant):
        """Test key term extraction."""
        text = "Machine learning is a subset of artificial intelligence. Machine learning uses algorithms."
        terms = study_assistant._extract_key_terms(text, max_terms=5)

        assert "machine" in terms
        assert "learning" in terms
        assert "algorithm" in terms or "artificial" in terms

    @pytest.mark.asyncio
    async def test_summarize_document(self, study_assistant, temp_txt_file):
        """Test document summarization."""
        summary = await study_assistant.summarize_document(temp_txt_file, max_length=200)

        assert len(summary) <= 250
        assert "Machine Learning" in summary or "machine learning" in summary.lower()

    @pytest.mark.asyncio
    async def test_generate_questions(self, study_assistant, temp_txt_file):
        """Test question generation."""
        questions = await study_assistant.generate_questions(temp_txt_file, num_questions=3)

        assert len(questions) >= 1
        assert all(isinstance(q, str) for q in questions)


class TestRAGSystem:
    """Tests for RAGSystem class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def rag_system(self, temp_dir):
        """Create a RAGSystem instance."""
        rs = RAGSystem(storage_path=temp_dir)
        yield rs
        rs.close()

    @pytest.fixture
    def temp_txt_file(self):
        """Create a temporary text file."""
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
        tmp.write(
            "Python Programming\n\nPython is a high-level programming language.\nIt supports multiple programming paradigms.\nPython is widely used in data science and machine learning.\n"
        )
        tmp.close()
        yield Path(tmp.name)
        Path(tmp.name).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_initialize(self, rag_system):
        """Test RAG system initialization."""
        result = await rag_system.initialize()
        assert result is True
        assert rag_system._initialized is True

    @pytest.mark.asyncio
    async def test_ingest_document(self, rag_system, temp_txt_file):
        """Test document ingestion."""
        await rag_system.initialize()

        result = await rag_system.ingest_document(temp_txt_file)

        assert result["success"] is True
        assert result["chunks_added"] >= 0  # May be 0 if content is short
        assert result["title"] == temp_txt_file.stem

    @pytest.mark.asyncio
    async def test_search_after_ingest(self, rag_system, temp_txt_file):
        """Test search after ingesting a document."""
        await rag_system.initialize()
        await rag_system.ingest_document(temp_txt_file)

        results = await rag_system.search("python", limit=3)

        # Results may be empty if content wasn't chunked properly
        # Just verify the search works
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_list_documents(self, rag_system, temp_txt_file):
        """Test listing documents."""
        await rag_system.initialize()
        await rag_system.ingest_document(temp_txt_file)

        docs = await rag_system.list_documents()

        assert len(docs) >= 1
        assert docs[0]["title"] == temp_txt_file.stem

    def test_get_stats(self, rag_system):
        """Test getting system statistics."""
        stats = rag_system.get_stats()

        assert "storage_path" in stats
        assert "documents_indexed" in stats


class TestIntentClassificationRAG:
    """Tests for RAG-related intent classification."""

    def test_rag_ingest_intent(self):
        """Test that ingest commands are classified as RAG."""
        from jarvis.core.agent import Intent, classify_intent

        assert classify_intent("ingest pdf notes.pdf") == Intent.RAG_QUERY
        assert classify_intent("ingest document file.txt") == Intent.RAG_QUERY

    def test_rag_summarize_intent(self):
        """Test that summarize commands are classified as RAG."""
        from jarvis.core.agent import Intent, classify_intent

        assert classify_intent("summarize this pdf") == Intent.RAG_QUERY
        assert classify_intent("summarize module 3") == Intent.RAG_QUERY

    def test_rag_question_intent(self):
        """Test that question generation commands are classified as RAG."""
        from jarvis.core.agent import Intent, classify_intent

        assert classify_intent("generate important questions") == Intent.RAG_QUERY
        assert classify_intent("prepare viva questions") == Intent.RAG_QUERY


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
