"""
Memory Engine for EmberOS.

Combines SQLite and ChromaDB for hybrid storage and retrieval.
"""

from __future__ import annotations

import logging
from typing import Any, Optional
from datetime import datetime

from emberos.core.config import MemoryConfig
from emberos.memory.sqlite_store import SQLiteStore
from emberos.memory.vector_store import VectorStore

logger = logging.getLogger(__name__)

# Global memory engine instance
_memory_engine: Optional["MemoryEngine"] = None


def get_memory_engine() -> Optional["MemoryEngine"]:
    """Get the global memory engine instance."""
    return _memory_engine


def set_memory_engine(engine: "MemoryEngine") -> None:
    """Set the global memory engine instance."""
    global _memory_engine
    _memory_engine = engine


class MemoryEngine:
    """
    Hybrid memory engine combining SQLite and ChromaDB.

    Provides:
    - Persistent storage for conversations, notes, patterns
    - Semantic search over stored content
    - Automatic embedding generation
    - Memory consolidation
    """

    def __init__(self, config: Optional[MemoryConfig] = None):
        self.config = config or MemoryConfig()
        self.sqlite = SQLiteStore()
        self.vector = VectorStore()
        self._started = False

    async def start(self) -> None:
        """Initialize the memory engine."""
        logger.info("Starting memory engine...")

        await self.sqlite.start()
        await self.vector.start()

        self._started = True
        set_memory_engine(self)

        logger.info("Memory engine started")

    async def stop(self) -> None:
        """Stop the memory engine."""
        logger.info("Stopping memory engine...")

        await self.sqlite.stop()
        await self.vector.stop()

        self._started = False
        set_memory_engine(None)

        logger.info("Memory engine stopped")

    @property
    def is_running(self) -> bool:
        """Check if memory engine is running."""
        return self._started

    # ============ Conversations ============

    async def store_conversation(
        self,
        user_message: str,
        agent_response: str,
        plan: Optional[Any] = None,
        results: Optional[list] = None,
        context: Optional[dict] = None,
        duration_ms: int = 0,
        success: bool = True
    ) -> str:
        """
        Store a conversation exchange.

        Stores in both SQLite (full data) and ChromaDB (for semantic search).
        """
        # Convert plan to dict if needed
        plan_dict = None
        if plan:
            plan_dict = plan.to_dict() if hasattr(plan, 'to_dict') else plan

        # Convert results to dicts if needed
        results_list = None
        if results:
            results_list = [
                r.to_dict() if hasattr(r, 'to_dict') else r
                for r in results
            ]

        # Store in SQLite
        conversation_id = await self.sqlite.store_conversation(
            user_message=user_message,
            agent_response=agent_response,
            plan=plan_dict,
            results=results_list,
            context=context,
            duration_ms=duration_ms,
            success=success
        )

        # Add to vector store for semantic search
        if self.vector.is_available:
            await self.vector.add_conversation(
                conversation_id=conversation_id,
                user_message=user_message,
                agent_response=agent_response
            )

        return conversation_id

    async def get_conversation(self, conversation_id: str) -> Optional[dict]:
        """Get a conversation by ID."""
        return await self.sqlite.get_conversation(conversation_id)

    async def get_recent_conversations(self, limit: int = 10) -> list[dict]:
        """Get recent conversations."""
        return await self.sqlite.get_recent_conversations(limit)

    async def search(self, query: str, limit: int = 10) -> list[dict]:
        """
        Search conversations using hybrid search.

        Combines keyword search (SQLite) with semantic search (ChromaDB).
        """
        results = []

        # Semantic search
        if self.vector.is_available:
            semantic_results = await self.vector.search_conversations(query, limit)
            for item in semantic_results:
                conv = await self.sqlite.get_conversation(item["id"])
                if conv:
                    conv["search_type"] = "semantic"
                    conv["relevance"] = 1.0 - (item.get("distance", 0) or 0)
                    results.append(conv)

        # Keyword search for additional results
        keyword_results = await self.sqlite.search_conversations(query, limit)

        # Merge results, avoiding duplicates
        seen_ids = {r["id"] for r in results}
        for conv in keyword_results:
            if conv["id"] not in seen_ids:
                conv["search_type"] = "keyword"
                conv["relevance"] = 0.5
                results.append(conv)

        # Sort by relevance
        results.sort(key=lambda x: x.get("relevance", 0), reverse=True)

        return results[:limit]

    # ============ Notes ============

    async def create_note(
        self,
        title: str,
        content: str = "",
        tags: Optional[list[str]] = None
    ) -> str:
        """Create a new note."""
        # Store in SQLite
        note_id = await self.sqlite.create_note(
            title=title,
            content=content,
            tags=tags
        )

        # Add to vector store
        if self.vector.is_available:
            await self.vector.add_note(
                note_id=note_id,
                title=title,
                content=content,
                tags=tags
            )

        return note_id

    async def get_note(self, note_id: str) -> Optional[dict]:
        """Get a note by ID."""
        return await self.sqlite.get_note(note_id)

    async def update_note(
        self,
        note_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[list[str]] = None
    ) -> bool:
        """Update a note."""
        # Update in SQLite
        success = await self.sqlite.update_note(
            note_id=note_id,
            title=title,
            content=content,
            tags=tags
        )

        # Update in vector store
        if success and self.vector.is_available:
            note = await self.sqlite.get_note(note_id)
            if note:
                await self.vector.update_note(
                    note_id=note_id,
                    title=note["title"],
                    content=note["content"],
                    tags=note.get("tags")
                )

        return success

    async def delete_note(self, note_id: str) -> bool:
        """Delete a note."""
        success = await self.sqlite.delete_note(note_id)

        if success and self.vector.is_available:
            await self.vector.delete_note(note_id)

        return success

    async def list_notes(
        self,
        limit: int = 50,
        tags: Optional[list[str]] = None,
        sort_by: str = "updated"
    ) -> list[dict]:
        """List notes."""
        return await self.sqlite.list_notes(limit=limit, tags=tags, sort_by=sort_by)

    async def search_notes(
        self,
        query: str,
        limit: int = 10,
        tags: Optional[list[str]] = None
    ) -> list[dict]:
        """Search notes with hybrid search."""
        results = []

        # Semantic search
        if self.vector.is_available:
            semantic_results = await self.vector.search_notes(query, limit, tags)
            for item in semantic_results:
                note = await self.sqlite.get_note(item["id"])
                if note:
                    note["search_type"] = "semantic"
                    note["relevance"] = 1.0 - (item.get("distance", 0) or 0)
                    results.append(note)

        # Keyword search
        keyword_results = await self.sqlite.search_notes(query, limit)

        seen_ids = {r["id"] for r in results}
        for note in keyword_results:
            if note["id"] not in seen_ids:
                note["search_type"] = "keyword"
                note["relevance"] = 0.5
                results.append(note)

        results.sort(key=lambda x: x.get("relevance", 0), reverse=True)

        return results[:limit]

    # ============ Tool Statistics ============

    async def record_tool_usage(
        self,
        tool_name: str,
        success: bool,
        duration_ms: int
    ) -> None:
        """Record tool usage statistics."""
        await self.sqlite.record_tool_usage(tool_name, success, duration_ms)

    async def get_tool_stats(self) -> list[dict]:
        """Get tool usage statistics."""
        return await self.sqlite.get_tool_stats()

    # ============ User Patterns ============

    async def store_pattern(
        self,
        pattern_type: str,
        pattern: dict,
        confidence: float = 0.5
    ) -> int:
        """Store a user pattern."""
        return await self.sqlite.store_pattern(pattern_type, pattern, confidence)

    async def get_patterns(self, pattern_type: Optional[str] = None) -> list[dict]:
        """Get user patterns."""
        return await self.sqlite.get_patterns(pattern_type)

    # ============ Context Building ============

    async def build_context(self, query: str, max_items: int = 5) -> dict:
        """
        Build context for LLM from memory.

        Retrieves relevant conversations and notes based on the query.
        """
        context = {
            "recent_conversations": [],
            "relevant_notes": [],
            "patterns": []
        }

        # Get recent conversations
        recent = await self.get_recent_conversations(limit=3)
        context["recent_conversations"] = [
            {
                "user": c["user_message"][:200],
                "agent": c["agent_response"][:200]
            }
            for c in recent
        ]

        # Search for relevant content
        if query:
            # Relevant notes
            notes = await self.search_notes(query, limit=max_items)
            context["relevant_notes"] = [
                {
                    "title": n["title"],
                    "content": n["content"][:300] if n.get("content") else "",
                    "tags": n.get("tags", [])
                }
                for n in notes
            ]

            # Relevant past conversations
            convs = await self.search(query, limit=max_items)
            context["similar_conversations"] = [
                {
                    "user": c["user_message"][:200],
                    "agent": c["agent_response"][:200]
                }
                for c in convs
            ]

        # Get relevant patterns
        patterns = await self.get_patterns()
        context["patterns"] = patterns[:3] if patterns else []

        return context

    # ============ Statistics ============

    async def get_stats(self) -> dict:
        """Get memory system statistics."""
        vector_stats = await self.vector.get_collection_stats() if self.vector.is_available else {}

        return {
            "vector_store": {
                "available": self.vector.is_available,
                "collections": vector_stats
            },
            "sqlite": {
                "available": True
            }
        }

