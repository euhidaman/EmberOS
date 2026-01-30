"""
Vector Store for EmberOS Memory.

Uses ChromaDB for semantic search over notes, conversations, and files.
"""

from __future__ import annotations

import logging
from typing import Any, Optional
from pathlib import Path

from emberos.core.constants import VECTOR_DB_PATH

logger = logging.getLogger(__name__)


class VectorStore:
    """
    ChromaDB-based vector store for semantic search.

    Collections:
    - notes: Note embeddings
    - conversations: Conversation embeddings
    - files: File content embeddings
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or VECTOR_DB_PATH
        self._client = None
        self._embedding_model = None
        self._collections: dict = {}

    async def start(self) -> None:
        """Initialize the vector store."""
        logger.info(f"Initializing vector store at {self.db_path}")

        try:
            import chromadb
            from chromadb.config import Settings
            import os

            # Ensure directory exists
            self.db_path.mkdir(parents=True, exist_ok=True)

            # Set cache directory to our writable data path (not /home/user/.cache)
            cache_dir = self.db_path / ".cache"
            cache_dir.mkdir(parents=True, exist_ok=True)

            # Set CHROMA_CACHE_DIR environment variable
            os.environ["CHROMA_CACHE_DIR"] = str(cache_dir)

            # Initialize ChromaDB
            self._client = chromadb.PersistentClient(
                path=str(self.db_path),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )

            # Create/get collections
            self._collections["notes"] = self._client.get_or_create_collection(
                name="notes",
                metadata={"description": "Note embeddings"}
            )

            self._collections["conversations"] = self._client.get_or_create_collection(
                name="conversations",
                metadata={"description": "Conversation embeddings"}
            )

            self._collections["files"] = self._client.get_or_create_collection(
                name="files",
                metadata={"description": "File content embeddings"}
            )

            logger.info("Vector store initialized with ChromaDB")

        except ImportError:
            logger.warning("ChromaDB not available, vector search disabled")
            self._client = None

    async def stop(self) -> None:
        """Close the vector store."""
        self._client = None
        self._collections = {}

    def _get_embedding_function(self):
        """Get the embedding function."""
        if self._embedding_model is None:
            try:
                from chromadb.utils import embedding_functions

                self._embedding_model = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="all-MiniLM-L6-v2"
                )
            except ImportError:
                logger.warning("SentenceTransformers not available")
                return None

        return self._embedding_model

    @property
    def is_available(self) -> bool:
        """Check if vector store is available."""
        return self._client is not None

    # ============ Notes ============

    async def add_note(
        self,
        note_id: str,
        title: str,
        content: str,
        tags: Optional[list[str]] = None
    ) -> Optional[str]:
        """Add a note to the vector store."""
        if not self.is_available:
            return None

        try:
            collection = self._collections["notes"]

            # Combine title and content for embedding
            text = f"{title}\n\n{content}"

            metadata = {
                "title": title,
                "tags": ",".join(tags) if tags else ""
            }

            collection.add(
                ids=[note_id],
                documents=[text],
                metadatas=[metadata]
            )

            return note_id

        except Exception as e:
            logger.error(f"Error adding note to vector store: {e}")
            return None

    async def update_note(
        self,
        note_id: str,
        title: str,
        content: str,
        tags: Optional[list[str]] = None
    ) -> bool:
        """Update a note in the vector store."""
        if not self.is_available:
            return False

        try:
            collection = self._collections["notes"]

            text = f"{title}\n\n{content}"

            metadata = {
                "title": title,
                "tags": ",".join(tags) if tags else ""
            }

            collection.update(
                ids=[note_id],
                documents=[text],
                metadatas=[metadata]
            )

            return True

        except Exception as e:
            logger.error(f"Error updating note in vector store: {e}")
            return False

    async def delete_note(self, note_id: str) -> bool:
        """Delete a note from the vector store."""
        if not self.is_available:
            return False

        try:
            collection = self._collections["notes"]
            collection.delete(ids=[note_id])
            return True
        except Exception as e:
            logger.error(f"Error deleting note from vector store: {e}")
            return False

    async def search_notes(
        self,
        query: str,
        limit: int = 10,
        tags: Optional[list[str]] = None
    ) -> list[dict]:
        """Search notes by semantic similarity."""
        if not self.is_available:
            return []

        try:
            collection = self._collections["notes"]

            where_filter = None
            if tags:
                # Filter by tags
                where_filter = {
                    "$or": [{"tags": {"$contains": tag}} for tag in tags]
                }

            results = collection.query(
                query_texts=[query],
                n_results=limit,
                where=where_filter
            )

            # Format results
            formatted = []
            if results["ids"] and results["ids"][0]:
                for i, note_id in enumerate(results["ids"][0]):
                    formatted.append({
                        "id": note_id,
                        "title": results["metadatas"][0][i].get("title", ""),
                        "distance": results["distances"][0][i] if results.get("distances") else None,
                        "content_preview": results["documents"][0][i][:200] if results.get("documents") else ""
                    })

            return formatted

        except Exception as e:
            logger.error(f"Error searching notes: {e}")
            return []

    # ============ Conversations ============

    async def add_conversation(
        self,
        conversation_id: str,
        user_message: str,
        agent_response: str
    ) -> Optional[str]:
        """Add a conversation to the vector store."""
        if not self.is_available:
            return None

        try:
            collection = self._collections["conversations"]

            # Combine for embedding
            text = f"User: {user_message}\n\nAssistant: {agent_response}"

            collection.add(
                ids=[conversation_id],
                documents=[text],
                metadatas=[{"user_message": user_message[:500]}]
            )

            return conversation_id

        except Exception as e:
            logger.error(f"Error adding conversation to vector store: {e}")
            return None

    async def search_conversations(
        self,
        query: str,
        limit: int = 10
    ) -> list[dict]:
        """Search conversations by semantic similarity."""
        if not self.is_available:
            return []

        try:
            collection = self._collections["conversations"]

            results = collection.query(
                query_texts=[query],
                n_results=limit
            )

            formatted = []
            if results["ids"] and results["ids"][0]:
                for i, conv_id in enumerate(results["ids"][0]):
                    formatted.append({
                        "id": conv_id,
                        "distance": results["distances"][0][i] if results.get("distances") else None,
                        "preview": results["documents"][0][i][:300] if results.get("documents") else ""
                    })

            return formatted

        except Exception as e:
            logger.error(f"Error searching conversations: {e}")
            return []

    # ============ Files ============

    async def add_file(
        self,
        file_path: str,
        content: str,
        metadata: Optional[dict] = None
    ) -> bool:
        """Add file content to the vector store."""
        if not self.is_available:
            return False

        try:
            collection = self._collections["files"]

            file_metadata = {
                "path": file_path,
                **(metadata or {})
            }

            collection.add(
                ids=[file_path],
                documents=[content],
                metadatas=[file_metadata]
            )

            return True

        except Exception as e:
            logger.error(f"Error adding file to vector store: {e}")
            return False

    async def search_files(
        self,
        query: str,
        limit: int = 10
    ) -> list[dict]:
        """Search files by semantic similarity."""
        if not self.is_available:
            return []

        try:
            collection = self._collections["files"]

            results = collection.query(
                query_texts=[query],
                n_results=limit
            )

            formatted = []
            if results["ids"] and results["ids"][0]:
                for i, file_path in enumerate(results["ids"][0]):
                    formatted.append({
                        "path": file_path,
                        "distance": results["distances"][0][i] if results.get("distances") else None,
                        "preview": results["documents"][0][i][:500] if results.get("documents") else ""
                    })

            return formatted

        except Exception as e:
            logger.error(f"Error searching files: {e}")
            return []

    # ============ General ============

    async def get_collection_stats(self) -> dict:
        """Get statistics about collections."""
        if not self.is_available:
            return {}

        stats = {}
        for name, collection in self._collections.items():
            stats[name] = {
                "count": collection.count()
            }

        return stats

