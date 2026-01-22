"""
Notes tools for EmberOS.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, Optional
from datetime import datetime
from pathlib import Path

from emberos.tools.base import (
    BaseTool, ToolResult, ToolManifest, ToolParameter,
    ToolCategory, RiskLevel
)
from emberos.tools.registry import register_tool


@register_tool
class NoteCreateTool(BaseTool):
    """Create a new note."""

    @property
    def manifest(self) -> ToolManifest:
        return ToolManifest(
            name="notes.create",
            description="Create a new note with title and content",
            category=ToolCategory.NOTES,
            icon="📝",
            parameters=[
                ToolParameter(
                    name="title",
                    type="string",
                    description="Note title",
                    required=True
                ),
                ToolParameter(
                    name="content",
                    type="string",
                    description="Note content",
                    required=False,
                    default=""
                ),
                ToolParameter(
                    name="tags",
                    type="list",
                    description="Tags for the note",
                    required=False,
                    default=[]
                )
            ],
            permissions=[],
            risk_level=RiskLevel.LOW
        )

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        title = params["title"]
        content = params.get("content", "")
        tags = params.get("tags", [])

        try:
            # Get memory engine from daemon context
            from emberos.memory.engine import get_memory_engine
            memory = get_memory_engine()

            if memory:
                note_id = await memory.create_note(
                    title=title,
                    content=content,
                    tags=tags
                )
            else:
                # Fallback: create note ID without storage
                note_id = str(uuid.uuid4())

            return ToolResult(
                success=True,
                data={
                    "id": note_id,
                    "title": title,
                    "content": content,
                    "tags": tags,
                    "created_at": datetime.now().isoformat()
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e), error_type=type(e).__name__)


@register_tool
class NoteSearchTool(BaseTool):
    """Search notes semantically."""

    @property
    def manifest(self) -> ToolManifest:
        return ToolManifest(
            name="notes.search",
            description="Search notes by content or tags (semantic search)",
            category=ToolCategory.NOTES,
            icon="🔎",
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Search query",
                    required=True
                ),
                ToolParameter(
                    name="limit",
                    type="int",
                    description="Maximum results",
                    required=False,
                    default=10
                ),
                ToolParameter(
                    name="tags",
                    type="list",
                    description="Filter by tags",
                    required=False
                )
            ],
            permissions=[],
            risk_level=RiskLevel.LOW
        )

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        query = params["query"]
        limit = params.get("limit", 10)
        tags = params.get("tags")

        try:
            from emberos.memory.engine import get_memory_engine
            memory = get_memory_engine()

            if memory:
                results = await memory.search_notes(
                    query=query,
                    limit=limit,
                    tags=tags
                )
            else:
                results = []

            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "results": results,
                    "count": len(results)
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e), error_type=type(e).__name__)


@register_tool
class NoteUpdateTool(BaseTool):
    """Update an existing note."""

    @property
    def manifest(self) -> ToolManifest:
        return ToolManifest(
            name="notes.update",
            description="Update an existing note",
            category=ToolCategory.NOTES,
            icon="✏️",
            parameters=[
                ToolParameter(
                    name="id",
                    type="string",
                    description="Note ID",
                    required=True
                ),
                ToolParameter(
                    name="title",
                    type="string",
                    description="New title",
                    required=False
                ),
                ToolParameter(
                    name="content",
                    type="string",
                    description="New content",
                    required=False
                ),
                ToolParameter(
                    name="tags",
                    type="list",
                    description="New tags",
                    required=False
                )
            ],
            permissions=[],
            risk_level=RiskLevel.LOW
        )

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        note_id = params["id"]

        try:
            from emberos.memory.engine import get_memory_engine
            memory = get_memory_engine()

            if memory:
                updates = {}
                if "title" in params:
                    updates["title"] = params["title"]
                if "content" in params:
                    updates["content"] = params["content"]
                if "tags" in params:
                    updates["tags"] = params["tags"]

                await memory.update_note(note_id, **updates)

                return ToolResult(
                    success=True,
                    data={
                        "id": note_id,
                        "updated_fields": list(updates.keys()),
                        "updated_at": datetime.now().isoformat()
                    }
                )
            else:
                return ToolResult(success=False, error="Memory engine not available")

        except Exception as e:
            return ToolResult(success=False, error=str(e), error_type=type(e).__name__)


@register_tool
class NoteDeleteTool(BaseTool):
    """Delete a note."""

    @property
    def manifest(self) -> ToolManifest:
        return ToolManifest(
            name="notes.delete",
            description="Delete a note",
            category=ToolCategory.NOTES,
            icon="🗑️",
            parameters=[
                ToolParameter(
                    name="id",
                    type="string",
                    description="Note ID",
                    required=True
                )
            ],
            permissions=[],
            risk_level=RiskLevel.MEDIUM,
            requires_confirmation=True,
            confirmation_message="Delete this note?"
        )

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        note_id = params["id"]

        try:
            from emberos.memory.engine import get_memory_engine
            memory = get_memory_engine()

            if memory:
                await memory.delete_note(note_id)

                return ToolResult(
                    success=True,
                    data={"id": note_id, "deleted": True}
                )
            else:
                return ToolResult(success=False, error="Memory engine not available")

        except Exception as e:
            return ToolResult(success=False, error=str(e), error_type=type(e).__name__)


@register_tool
class NoteListTool(BaseTool):
    """List all notes."""

    @property
    def manifest(self) -> ToolManifest:
        return ToolManifest(
            name="notes.list",
            description="List all notes with optional filtering",
            category=ToolCategory.NOTES,
            icon="📋",
            parameters=[
                ToolParameter(
                    name="limit",
                    type="int",
                    description="Maximum results",
                    required=False,
                    default=50
                ),
                ToolParameter(
                    name="tags",
                    type="list",
                    description="Filter by tags",
                    required=False
                ),
                ToolParameter(
                    name="sort_by",
                    type="string",
                    description="Sort field: 'created', 'updated', 'title'",
                    required=False,
                    default="updated",
                    choices=["created", "updated", "title"]
                )
            ],
            permissions=[],
            risk_level=RiskLevel.LOW
        )

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        limit = params.get("limit", 50)
        tags = params.get("tags")
        sort_by = params.get("sort_by", "updated")

        try:
            from emberos.memory.engine import get_memory_engine
            memory = get_memory_engine()

            if memory:
                notes = await memory.list_notes(
                    limit=limit,
                    tags=tags,
                    sort_by=sort_by
                )
            else:
                notes = []

            return ToolResult(
                success=True,
                data={
                    "notes": notes,
                    "count": len(notes)
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e), error_type=type(e).__name__)

