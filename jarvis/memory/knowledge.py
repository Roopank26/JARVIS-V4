"""
Local knowledge base for JARVIS.
Provides semantic search using vector embeddings with robust fallback.
"""

import json
import re
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeEntry:
    """A knowledge base entry."""
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)


class TFIDFVectorStore:
    """
    TF-IDF based vector store that works without external dependencies.
    Provides semantic-like search using term frequency-inverse document frequency.
    """
    
    def __init__(self):
        self.entries: Dict[str, Dict] = {}
        self._term_doc_freq: Dict[str, int] = defaultdict(int)
        self._doc_count = 0
        self._stop_words: Set[str] = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'was', 'are', 'be', 'been', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we',
            'they', 'what', 'which', 'who', 'when', 'where', 'why', 'how'
        }
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words."""
        text = text.lower()
        words = re.findall(r'\b\w+\b', text)
        return [w for w in words if w not in self._stop_words and len(w) > 2]
    
    def _compute_tf(self, tokens: List[str]) -> Dict[str, float]:
        """Compute term frequency."""
        if not tokens:
            return {}
        tf = defaultdict(int)
        for token in tokens:
            tf[token] += 1
        return {t: c / len(tokens) for t, c in tf.items()}
    
    def _update_idf(self, tokens: Set[str]) -> None:
        """Update inverse document frequency."""
        for token in tokens:
            self._term_doc_freq[token] += 1
    
    def add(self, entry_id: str, content: str, metadata: Dict[str, Any]) -> None:
        """Add an entry."""
        tokens = self._tokenize(content)
        self._update_idf(set(tokens))
        
        self.entries[entry_id] = {
            'id': entry_id,
            'content': content,
            'metadata': metadata,
            'tokens': set(tokens),
            'tf': self._compute_tf(tokens),
            'created_at': datetime.now().isoformat()
        }
        self._doc_count += 1
    
    def search(self, query: str, limit: int = 5) -> List[Dict]:
        """Search using TF-IDF scoring."""
        if not self.entries or not query:
            return []
        
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []
        
        query_tf = self._compute_tf(query_tokens)
        scores = {}
        
        for doc_id, entry in self.entries.items():
            score = 0.0
            for token, query_weight in query_tf.items():
                doc_tf = entry['tf'].get(token, 0)
                idf = max(1.0, self._doc_count / (1 + self._term_doc_freq.get(token, 0)))
                score += doc_tf * idf * query_weight
            
            content_lower = entry['content'].lower()
            for token in query_tokens:
                if token in content_lower:
                    score += 0.1
            
            scores[doc_id] = score
        
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        
        return [
            {
                'id': entry['id'],
                'content': entry['content'],
                'score': scores[entry['id']],
                'metadata': entry['metadata']
            }
            for entry_id in sorted_ids[:limit]
            if (entry := self.entries.get(entry_id))
        ]
    
    def delete(self, entry_id: str) -> bool:
        """Delete an entry."""
        if entry_id in self.entries:
            del self.entries[entry_id]
            self._doc_count -= 1
            return True
        return False
    
    def count(self) -> int:
        """Get entry count."""
        return len(self.entries)
    
    def clear(self) -> None:
        """Clear all entries."""
        self.entries = {}
        self._term_doc_freq = defaultdict(int)
        self._doc_count = 0


class LocalKnowledgeBase:
    """Local knowledge base with semantic search using ChromaDB with TF-IDF fallback."""

    def __init__(self, storage_path: Path = None):
        self.storage_path = storage_path or Path.home() / ".jarvis" / "knowledge"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self._chromadb = None
        self._embedding_model = None
        self._collection = None
        self._initialized = False
        self._use_chroma = False
        self._tfidf_store = TFIDFVectorStore()
        self._metadata: Dict[str, Dict] = {}

    async def initialize(self) -> bool:
        """Initialize the knowledge base."""
        if self._initialized:
            return True
        
        chroma_ok = await self._init_chromadb()
        self._use_chroma = chroma_ok
        self._load_from_disk()
        self._initialized = True
        return True
    
    async def _init_chromadb(self) -> bool:
        """Initialize ChromaDB."""
        try:
            import chromadb
            from chromadb.config import Settings
            from sentence_transformers import SentenceTransformer
            
            self._chromadb = chromadb.PersistentClient(
                path=str(self.storage_path / "chroma_db"),
                settings=Settings(anonymized_telemetry=False)
            )
            self._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            self._collection = self._chromadb.get_or_create_collection(
                name="jarvis_knowledge",
                metadata={"description": "JARVIS knowledge base"}
            )
            logger.info("Knowledge base initialized with ChromaDB")
            return True
        except Exception as e:
            logger.info(f"ChromaDB not available, using TF-IDF: {e}")
            return False

    def _load_from_disk(self) -> None:
        """Load data from disk."""
        metadata_file = self.storage_path / "knowledge_metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, "r") as f:
                    self._metadata = json.load(f)
                for entry_id, data in self._metadata.items():
                    if "content" in data:
                        self._tfidf_store.add(entry_id, data["content"], data.get("metadata", {}))
                logger.info(f"Loaded {len(self._metadata)} entries from disk")
            except Exception as e:
                logger.warning(f"Failed to load from disk: {e}")
                self._metadata = {}

    def _save_to_disk(self) -> None:
        """Save metadata to disk."""
        try:
            metadata_file = self.storage_path / "knowledge_metadata.json"
            with open(metadata_file, "w") as f:
                json.dump(self._metadata, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save to disk: {e}")

    def _generate_id(self, content: str) -> str:
        """Generate unique ID."""
        hash_input = f"{content[:100]}_{datetime.now().timestamp()}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:16]

    async def add(self, content: str, tags: Optional[List[str]] = None,
                  metadata: Optional[Dict[str, Any]] = None,
                  source: str = "") -> str:
        """Add a knowledge entry."""
        entry_id = self._generate_id(content)
        full_metadata = {
            "tags": tags or [], 
            "source": source,
            **(metadata or {}), 
            "created_at": datetime.now().isoformat()
        }
        
        self._tfidf_store.add(entry_id, content, full_metadata)
        self._metadata[entry_id] = {"content": content, "metadata": full_metadata}
        
        if self._use_chroma and self._collection:
            try:
                embedding = self._embedding_model.encode([content])[0]
                self._collection.add(
                    documents=[content],
                    embeddings=[embedding.tolist()],
                    metadatas=[full_metadata],
                    ids=[entry_id]
                )
            except Exception as e:
                logger.debug(f"ChromaDB add failed: {e}")
        
        self._save_to_disk()
        return entry_id
    
    async def get(self, entry_id: str) -> Optional[Dict]:
        """Get an entry by ID."""
        if entry_id in self._metadata:
            data = self._metadata[entry_id]
            return {
                "id": entry_id,
                "content": data["content"],
                "metadata": data.get("metadata", {})
            }
        return None

    async def search(self, query: str, limit: int = 5, tags: Optional[List[str]] = None) -> List[Dict]:
        """Search the knowledge base."""
        results = []
        
        if self._use_chroma and self._collection:
            try:
                query_embedding = self._embedding_model.encode([query])[0]
                chroma_results = self._collection.query(
                    query_embeddings=[query_embedding.tolist()],
                    n_results=limit * 2
                )
                for i, doc in enumerate(chroma_results.get("documents", [[]])[0]):
                    entry_id = chroma_results["ids"][0][i]
                    distance = chroma_results.get("distances", [[]])[0][i]
                    meta = chroma_results.get("metadatas", [[]])[0][i] or {}
                    if tags and not any(t in meta.get("tags", []) for t in tags):
                        continue
                    results.append({"id": entry_id, "content": doc, "score": 1.0 - (distance or 0), "metadata": meta})
                    if len(results) >= limit:
                        break
            except Exception as e:
                logger.debug(f"ChromaDB search failed: {e}")
        
        if not results:
            tfidf_results = self._tfidf_store.search(query, limit)
            for result in tfidf_results:
                if tags and not any(t in result.get("metadata", {}).get("tags", []) for t in tags):
                    continue
                results.append(result)
        
        return results[:limit]

    async def add_project_context(self, project_path: Path, max_file_size: int = 50000) -> int:
        """Index project files for search."""
        if not project_path.exists():
            return 0
        
        indexed = 0
        file_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.md', '.txt', '.json', '.yaml', 
                          '.yml', '.toml', '.ini', '.cfg', '.sh', '.bash', '.zsh', '.c', '.cpp',
                          '.h', '.hpp', '.java', '.go', '.rs', '.rb', '.php', '.cs', '.swift',
                          '.kt', '.scala', '.r', '.lua', '.pl'}
        skip_dirs = {'.git', '__pycache__', 'node_modules', 'venv', '.venv', 'build', 'dist',
                    '.idea', '.vscode', 'target', 'bin', 'obj', '.gradle', '.maven', 'coverage'}
        skip_files = {'package-lock.json', 'yarn.lock', 'poetry.lock', 'requirements.txt'}
        
        for file_path in project_path.rglob('*'):
            if not file_path.is_file() or any(s in file_path.parts for s in skip_dirs):
                continue
            if file_path.name in skip_files or file_path.suffix.lower() not in file_extensions:
                continue
            try:
                if file_path.stat().st_size > max_file_size:
                    continue
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                if not content.strip() or len(content) > max_file_size:
                    continue
                rel_path = file_path.relative_to(project_path)
                await self.add(
                    content=f"File: {file_path.name}\nPath: {rel_path}\n\n{content[:5000]}",
                    tags=["project", file_path.suffix[1:].lower(), project_path.name],
                    metadata={"file": str(rel_path), "project": project_path.name}
                )
                indexed += 1
            except Exception:
                pass
        
        logger.info(f"Indexed {indexed} files from {project_path}")
        return indexed

    async def delete(self, entry_id: str) -> bool:
        """Delete an entry."""
        if entry_id not in self._metadata:
            return False
        del self._metadata[entry_id]
        self._tfidf_store.delete(entry_id)
        if self._use_chroma and self._collection:
            try:
                self._collection.delete(ids=[entry_id])
            except Exception:
                pass
        self._save_to_disk()
        return True

    async def count(self) -> int:
        """Get total number of entries."""
        return self._tfidf_store.count()

    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        total = self._tfidf_store.count()
        if self._use_chroma and self._collection:
            try:
                total = max(total, self._collection.count())
            except Exception:
                pass
        tag_counts = defaultdict(int)
        for entry in self._metadata.values():
            for tag in entry.get("metadata", {}).get("tags", []):
                tag_counts[tag] += 1
        return {
            "total_entries": total,
            "chroma_available": self._use_chroma,
            "storage_type": "chroma" if self._use_chroma else "tfidf_disk",
            "top_tags": dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10])
        }

    async def clear(self) -> None:
        """Clear all entries."""
        self._tfidf_store.clear()
        self._metadata = {}
        self._save_to_disk()
        if self._use_chroma and self._collection:
            try:
                self._chromadb.delete_collection("jarvis_knowledge")
                self._collection = self._chromadb.get_or_create_collection(name="jarvis_knowledge")
            except Exception as e:
                logger.error(f"Failed to clear ChromaDB: {e}")
