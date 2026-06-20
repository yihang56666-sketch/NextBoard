"""Chip manual RAG system using LlamaIndex.

Provides semantic search and Q&A over chip datasheets, reference manuals,
and application notes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from llama_index.core import (
        SimpleDirectoryReader,
        StorageContext,
        VectorStoreIndex,
        load_index_from_storage,
    )
    LLAMA_INDEX_AVAILABLE = True
except ImportError:
    LLAMA_INDEX_AVAILABLE = False

from logger import get_logger

logger = get_logger(__name__)


class ChipManualRAG:
    """RAG system for chip documentation."""

    def __init__(self, chip_docs_dir: Path, cache_dir: Path | None = None):
        """Initialize RAG system.

        Args:
            chip_docs_dir: Directory containing chip documentation
            cache_dir: Optional cache directory for index persistence
        """
        if not LLAMA_INDEX_AVAILABLE:
            raise RuntimeError("llama-index not installed. Run: pip install llama-index")

        self.chip_docs_dir = Path(chip_docs_dir)
        self.cache_dir = Path(cache_dir) if cache_dir else self.chip_docs_dir / ".index_cache"
        self.index: Any | None = None

        logger.info(f"Initialized ChipManualRAG for {chip_docs_dir}")

    def build_index(self, force_rebuild: bool = False) -> None:
        """Build or load vector index.

        Args:
            force_rebuild: Force rebuild even if cache exists
        """
        # Check cache
        if not force_rebuild and (self.cache_dir / "docstore.json").exists():
            logger.info("Loading index from cache")
            storage_context = StorageContext.from_defaults(persist_dir=str(self.cache_dir))
            self.index = load_index_from_storage(storage_context)
            return

        # Build new index
        logger.info("Building new index from documents")

        if not self.chip_docs_dir.exists():
            raise FileNotFoundError(f"Documentation directory not found: {self.chip_docs_dir}")

        # Load documents
        documents = SimpleDirectoryReader(
            str(self.chip_docs_dir),
            recursive=True,
            required_exts=[".pdf", ".md", ".txt"],
        ).load_data()

        logger.info(f"Loaded {len(documents)} documents")

        # Create index
        self.index = VectorStoreIndex.from_documents(documents)

        # Persist to cache
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index.storage_context.persist(persist_dir=str(self.cache_dir))

        logger.info("Index built and cached")

    def query(self, question: str, top_k: int = 3) -> dict[str, Any]:
        """Query the RAG system.

        Args:
            question: User question
            top_k: Number of relevant chunks to retrieve

        Returns:
            Query result with answer and sources
        """
        if self.index is None:
            self.build_index()
        if self.index is None:
            raise RuntimeError("RAG index was not initialized")

        query_engine = self.index.as_query_engine(similarity_top_k=top_k)
        response = query_engine.query(question)

        # Extract source information
        sources: list[dict[str, Any]] = []
        for node in response.source_nodes:
            sources.append({
                "text": node.node.get_content()[:200] + "...",
                "score": node.score,
                "metadata": node.node.metadata,
            })

        return {
            "question": question,
            "answer": str(response),
            "sources": sources,
            "confidence": sources[0]["score"] if sources else 0.0,
        }

    def summarize_chip(self, chip_part: str) -> dict[str, Any]:
        """Generate comprehensive chip summary.

        Args:
            chip_part: Chip part number (e.g., 'STM32F407VG')

        Returns:
            Structured chip summary
        """
        if self.index is None:
            self.build_index()

        # Query for key information
        queries = {
            "overview": f"What is {chip_part}? Provide a brief overview.",
            "peripherals": f"List the main peripherals of {chip_part}.",
            "memory": f"Describe the memory configuration of {chip_part}.",
            "power": f"What are the power supply requirements for {chip_part}?",
            "clock": f"Describe the clock tree and frequency options for {chip_part}.",
        }

        summary: dict[str, Any] = {"chip": chip_part, "sections": {}}

        for section, query in queries.items():
            result = self.query(query, top_k=2)
            summary["sections"][section] = {
                "answer": result["answer"],
                "confidence": result["confidence"],
            }

        return summary


# Integration with chip_dossier.py
def query_chip_manual(chip_docs_dir: Path, question: str) -> str:
    """Convenience function for chip_dossier integration.

    Args:
        chip_docs_dir: Directory with chip docs
        question: Question to ask

    Returns:
        Answer string
    """
    rag = ChipManualRAG(chip_docs_dir)
    result = rag.query(question)
    return str(result["answer"])


# Example usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python chip_manual_rag.py <docs_dir> <question>")
        sys.exit(1)

    docs_dir = Path(sys.argv[1])
    question = sys.argv[2]

    rag = ChipManualRAG(docs_dir)
    result = rag.query(question)

    print(f"Question: {result['question']}")
    print(f"Answer: {result['answer']}")
    print(f"Confidence: {result['confidence']:.2f}")
    print(f"\nSources: {len(result['sources'])} documents")
