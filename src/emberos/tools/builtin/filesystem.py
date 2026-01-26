"""
Filesystem tools for EmberOS.
"""

from __future__ import annotations

import os
import shutil
import fnmatch
import csv
import json
import base64
from pathlib import Path
from typing import Any, Optional
from datetime import datetime

from emberos.tools.base import (
    BaseTool, ToolResult, ToolManifest, ToolParameter,
    ToolCategory, RiskLevel
)
from emberos.tools.registry import register_tool


@register_tool
class FileSearchTool(BaseTool):
    """Search for files by name or content."""

    @property
    def manifest(self) -> ToolManifest:
        return ToolManifest(
            name="filesystem.search",
            description="Search for files by name pattern or content",
            category=ToolCategory.FILESYSTEM,
            icon="🔍",
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Search query (file name pattern or content)",
                    required=True
                ),
                ToolParameter(
                    name="path",
                    type="string",
                    description="Directory to search in",
                    required=False,
                    default="~"
                ),
                ToolParameter(
                    name="extensions",
                    type="list",
                    description="File extensions to include (e.g., ['.txt', '.pdf'])",
                    required=False
                ),
                ToolParameter(
                    name="max_results",
                    type="int",
                    description="Maximum number of results",
                    required=False,
                    default=50
                ),
                ToolParameter(
                    name="search_content",
                    type="bool",
                    description="Search within file contents",
                    required=False,
                    default=False
                )
            ],
            permissions=["filesystem:read"],
            risk_level=RiskLevel.LOW
        )

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        query = params["query"]
        path = os.path.expanduser(params.get("path", "~"))
        extensions = params.get("extensions", [])
        max_results = params.get("max_results", 50)
        search_content = params.get("search_content", False)

        results = []

        try:
            path = Path(path)
            if not path.exists():
                return ToolResult(success=False, error=f"Path does not exist: {path}")

            # Search for files
            for root, dirs, files in os.walk(path):
                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.')]

                for filename in files:
                    if len(results) >= max_results:
                        break

                    # Check extension filter
                    if extensions:
                        ext = Path(filename).suffix.lower()
                        if ext not in [e.lower() for e in extensions]:
                            continue

                    filepath = Path(root) / filename

                    # Check filename match
                    if fnmatch.fnmatch(filename.lower(), f"*{query.lower()}*"):
                        results.append(self._file_info(filepath))
                        continue

                    # Search content if requested
                    if search_content:
                        try:
                            with open(filepath, 'r', errors='ignore') as f:
                                content = f.read(10000)  # First 10KB
                                if query.lower() in content.lower():
                                    results.append(self._file_info(filepath))
                        except (OSError, IOError):
                            pass

            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "path": str(path),
                    "results": results,
                    "count": len(results)
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e), error_type=type(e).__name__)

    def _file_info(self, path: Path) -> dict:
        """Get file information."""
        stat = path.stat()
        return {
            "name": path.name,
            "path": str(path),
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "is_dir": path.is_dir()
        }


@register_tool
class FileReadTool(BaseTool):
    """Read file contents."""

    @property
    def manifest(self) -> ToolManifest:
        return ToolManifest(
            name="filesystem.read",
            description="Read the contents of a file",
            category=ToolCategory.FILESYSTEM,
            icon="📄",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the file to read",
                    required=True
                ),
                ToolParameter(
                    name="encoding",
                    type="string",
                    description="File encoding",
                    required=False,
                    default="utf-8"
                ),
                ToolParameter(
                    name="max_size",
                    type="int",
                    description="Maximum bytes to read",
                    required=False,
                    default=100000
                )
            ],
            permissions=["filesystem:read"],
            risk_level=RiskLevel.LOW
        )

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        path = os.path.expanduser(params["path"])
        encoding = params.get("encoding", "utf-8")
        max_size = params.get("max_size", 100000)

        try:
            filepath = Path(path)

            if not filepath.exists():
                return ToolResult(success=False, error=f"File not found: {path}")

            if filepath.is_dir():
                return ToolResult(success=False, error=f"Path is a directory: {path}")

            stat = filepath.stat()

            with open(filepath, 'r', encoding=encoding, errors='replace') as f:
                content = f.read(max_size)

            truncated = stat.st_size > max_size

            return ToolResult(
                success=True,
                data={
                    "path": str(filepath),
                    "content": content,
                    "size": stat.st_size,
                    "truncated": truncated,
                    "encoding": encoding
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e), error_type=type(e).__name__)


@register_tool
class FileWriteTool(BaseTool):
    """Write content to a file."""

    @property
    def manifest(self) -> ToolManifest:
        return ToolManifest(
            name="filesystem.write",
            description="Write content to a file",
            category=ToolCategory.FILESYSTEM,
            icon="✏️",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to write to",
                    required=True
                ),
                ToolParameter(
                    name="content",
                    type="string",
                    description="Content to write",
                    required=True
                ),
                ToolParameter(
                    name="mode",
                    type="string",
                    description="Write mode: 'overwrite' or 'append'",
                    required=False,
                    default="overwrite",
                    choices=["overwrite", "append"]
                ),
                ToolParameter(
                    name="create_dirs",
                    type="bool",
                    description="Create parent directories if needed",
                    required=False,
                    default=True
                )
            ],
            permissions=["filesystem:write"],
            risk_level=RiskLevel.MEDIUM,
            requires_confirmation=True,
            confirmation_message="Write to file: {path}?"
        )

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        path = os.path.expanduser(params["path"])
        content = params["content"]
        mode = params.get("mode", "overwrite")
        create_dirs = params.get("create_dirs", True)

        try:
            filepath = Path(path)

            if create_dirs:
                filepath.parent.mkdir(parents=True, exist_ok=True)

            write_mode = "w" if mode == "overwrite" else "a"

            with open(filepath, write_mode, encoding="utf-8") as f:
                f.write(content)

            return ToolResult(
                success=True,
                data={
                    "path": str(filepath),
                    "bytes_written": len(content.encode("utf-8")),
                    "mode": mode
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e), error_type=type(e).__name__)


@register_tool
class FileMoveTool(BaseTool):
    """Move or rename files."""

    @property
    def manifest(self) -> ToolManifest:
        return ToolManifest(
            name="filesystem.move",
            description="Move or rename files and directories",
            category=ToolCategory.FILESYSTEM,
            icon="📦",
            parameters=[
                ToolParameter(
                    name="source",
                    type="string",
                    description="Source path",
                    required=True
                ),
                ToolParameter(
                    name="destination",
                    type="string",
                    description="Destination path",
                    required=True
                ),
                ToolParameter(
                    name="overwrite",
                    type="bool",
                    description="Overwrite existing files",
                    required=False,
                    default=False
                )
            ],
            permissions=["filesystem:read", "filesystem:write"],
            risk_level=RiskLevel.MEDIUM,
            requires_confirmation=True,
            confirmation_message="Move {source} to {destination}?"
        )

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        source = os.path.expanduser(params["source"])
        destination = os.path.expanduser(params["destination"])
        overwrite = params.get("overwrite", False)

        try:
            src_path = Path(source)
            dst_path = Path(destination)

            if not src_path.exists():
                return ToolResult(success=False, error=f"Source not found: {source}")

            if dst_path.exists() and not overwrite:
                return ToolResult(success=False, error=f"Destination exists: {destination}")

            # Create destination parent if needed
            dst_path.parent.mkdir(parents=True, exist_ok=True)

            shutil.move(str(src_path), str(dst_path))

            return ToolResult(
                success=True,
                data={
                    "source": str(src_path),
                    "destination": str(dst_path)
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e), error_type=type(e).__name__)


@register_tool
class FileDeleteTool(BaseTool):
    """Delete files or directories."""

    @property
    def manifest(self) -> ToolManifest:
        return ToolManifest(
            name="filesystem.delete",
            description="Delete files or directories",
            category=ToolCategory.FILESYSTEM,
            icon="🗑️",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to delete",
                    required=True
                ),
                ToolParameter(
                    name="recursive",
                    type="bool",
                    description="Delete directories recursively",
                    required=False,
                    default=False
                )
            ],
            permissions=["filesystem:write"],
            risk_level=RiskLevel.HIGH,
            requires_confirmation=True,
            confirmation_message="Delete {path}? This cannot be undone."
        )

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        path = os.path.expanduser(params["path"])
        recursive = params.get("recursive", False)

        try:
            target = Path(path)

            if not target.exists():
                return ToolResult(success=False, error=f"Path not found: {path}")

            if target.is_dir():
                if recursive:
                    shutil.rmtree(target)
                else:
                    target.rmdir()
            else:
                target.unlink()

            return ToolResult(
                success=True,
                data={
                    "path": str(target),
                    "was_directory": target.is_dir() if target.exists() else False
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e), error_type=type(e).__name__)


@register_tool
class DirectoryListTool(BaseTool):
    """List directory contents."""

    @property
    def manifest(self) -> ToolManifest:
        return ToolManifest(
            name="filesystem.list",
            description="List contents of a directory",
            category=ToolCategory.FILESYSTEM,
            icon="📂",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Directory path",
                    required=True
                ),
                ToolParameter(
                    name="recursive",
                    type="bool",
                    description="List recursively",
                    required=False,
                    default=False
                ),
                ToolParameter(
                    name="show_hidden",
                    type="bool",
                    description="Show hidden files",
                    required=False,
                    default=False
                ),
                ToolParameter(
                    name="max_depth",
                    type="int",
                    description="Maximum recursion depth",
                    required=False,
                    default=3
                )
            ],
            permissions=["filesystem:read"],
            risk_level=RiskLevel.LOW
        )

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        path = os.path.expanduser(params["path"])
        recursive = params.get("recursive", False)
        show_hidden = params.get("show_hidden", False)
        max_depth = params.get("max_depth", 3)

        try:
            directory = Path(path)

            if not directory.exists():
                return ToolResult(success=False, error=f"Directory not found: {path}")

            if not directory.is_dir():
                return ToolResult(success=False, error=f"Not a directory: {path}")

            items = self._list_dir(directory, recursive, show_hidden, max_depth, 0)

            return ToolResult(
                success=True,
                data={
                    "path": str(directory),
                    "items": items,
                    "count": len(items)
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e), error_type=type(e).__name__)

    def _list_dir(
        self,
        path: Path,
        recursive: bool,
        show_hidden: bool,
        max_depth: int,
        current_depth: int
    ) -> list[dict]:
        """List directory contents."""
        items = []

        try:
            for item in sorted(path.iterdir()):
                if not show_hidden and item.name.startswith('.'):
                    continue

                stat = item.stat()
                entry = {
                    "name": item.name,
                    "path": str(item),
                    "is_dir": item.is_dir(),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                }

                if item.is_dir() and recursive and current_depth < max_depth:
                    entry["children"] = self._list_dir(
                        item, recursive, show_hidden, max_depth, current_depth + 1
                    )

                items.append(entry)

        except PermissionError:
            pass

        return items


@register_tool
class FileOrganizeTool(BaseTool):
    """Organize files by type."""

    @property
    def manifest(self) -> ToolManifest:
        return ToolManifest(
            name="filesystem.organize",
            description="Organize files in a directory by type",
            category=ToolCategory.FILESYSTEM,
            icon="📁",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Directory to organize",
                    required=True
                ),
                ToolParameter(
                    name="dry_run",
                    type="bool",
                    description="Preview without making changes",
                    required=False,
                    default=True
                )
            ],
            permissions=["filesystem:read", "filesystem:write"],
            risk_level=RiskLevel.MEDIUM,
            requires_confirmation=True,
            confirmation_message="Organize files in {path}?"
        )

    # Extension to category mapping
    CATEGORIES = {
        "Documents": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xls", ".xlsx", ".ppt", ".pptx"],
        "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico"],
        "Videos": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"],
        "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"],
        "Archives": [".zip", ".tar", ".gz", ".rar", ".7z", ".bz2"],
        "Code": [".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".rs", ".go"],
        "Data": [".json", ".xml", ".csv", ".yaml", ".yml", ".sql", ".db"],
    }

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        path = os.path.expanduser(params["path"])
        dry_run = params.get("dry_run", True)

        try:
            directory = Path(path)

            if not directory.exists():
                return ToolResult(success=False, error=f"Directory not found: {path}")

            # Plan organization
            plan = []
            for item in directory.iterdir():
                if item.is_file():
                    ext = item.suffix.lower()
                    category = self._get_category(ext)

                    if category:
                        dest_dir = directory / category
                        dest_path = dest_dir / item.name

                        plan.append({
                            "source": str(item),
                            "destination": str(dest_path),
                            "category": category
                        })

            # Execute if not dry run
            moved = []
            if not dry_run:
                for move in plan:
                    src = Path(move["source"])
                    dst = Path(move["destination"])

                    dst.parent.mkdir(exist_ok=True)
                    shutil.move(str(src), str(dst))
                    moved.append(move)

            return ToolResult(
                success=True,
                data={
                    "path": str(directory),
                    "planned": plan,
                    "moved": moved if not dry_run else [],
                    "dry_run": dry_run,
                    "file_count": len(plan)
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e), error_type=type(e).__name__)

    def _get_category(self, extension: str) -> Optional[str]:
        """Get category for file extension."""
        for category, extensions in self.CATEGORIES.items():
            if extension in extensions:
                return category
        return None


@register_tool
class CreateDirectoryTool(BaseTool):
    """Create a new directory."""

    @property
    def manifest(self) -> ToolManifest:
        return ToolManifest(
            name="filesystem.create_directory",
            description="Create a new directory (and parent directories if needed)",
            category=ToolCategory.FILESYSTEM,
            icon="📁",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path for the new directory",
                    required=True
                ),
                ToolParameter(
                    name="parents",
                    type="bool",
                    description="Create parent directories if they don't exist",
                    required=False,
                    default=True
                )
            ],
            permissions=["filesystem:write"],
            risk_level=RiskLevel.LOW
        )

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        path = os.path.expanduser(params["path"])
        parents = params.get("parents", True)

        try:
            directory = Path(path)

            if directory.exists():
                return ToolResult(
                    success=True,
                    data={
                        "path": str(directory),
                        "created": False,
                        "message": "Directory already exists"
                    }
                )

            directory.mkdir(parents=parents, exist_ok=True)

            return ToolResult(
                success=True,
                data={
                    "path": str(directory),
                    "created": True,
                    "message": f"Created directory: {path}"
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e), error_type=type(e).__name__)


@register_tool
class CreateSpreadsheetTool(BaseTool):
    """Create a new spreadsheet (CSV format)."""

    @property
    def manifest(self) -> ToolManifest:
        return ToolManifest(
            name="filesystem.create_spreadsheet",
            description="Create a new spreadsheet file (CSV format) with optional headers and data",
            category=ToolCategory.FILESYSTEM,
            icon="📊",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path for the spreadsheet file (will add .csv extension if not present)",
                    required=True
                ),
                ToolParameter(
                    name="headers",
                    type="list",
                    description="Column headers (e.g., ['Name', 'Date', 'Amount'])",
                    required=False,
                    default=[]
                ),
                ToolParameter(
                    name="rows",
                    type="list",
                    description="Data rows (list of lists)",
                    required=False,
                    default=[]
                ),
                ToolParameter(
                    name="template",
                    type="string",
                    description="Template type: 'budget', 'inventory', 'contacts', 'tasks', or 'blank'",
                    required=False,
                    default="blank",
                    choices=["budget", "inventory", "contacts", "tasks", "blank"]
                )
            ],
            permissions=["filesystem:write"],
            risk_level=RiskLevel.LOW
        )

    # Predefined templates
    TEMPLATES = {
        "budget": {
            "headers": ["Category", "Description", "Amount", "Date", "Type", "Notes"],
            "rows": [
                ["Income", "Salary", "", "", "Income", ""],
                ["Housing", "Rent/Mortgage", "", "", "Expense", ""],
                ["Utilities", "Electricity", "", "", "Expense", ""],
                ["Utilities", "Water", "", "", "Expense", ""],
                ["Food", "Groceries", "", "", "Expense", ""],
                ["Transportation", "Gas/Fuel", "", "", "Expense", ""],
            ]
        },
        "inventory": {
            "headers": ["Item", "Category", "Quantity", "Unit Price", "Total Value", "Location", "Last Updated"],
            "rows": []
        },
        "contacts": {
            "headers": ["Name", "Email", "Phone", "Company", "Address", "Notes"],
            "rows": []
        },
        "tasks": {
            "headers": ["Task", "Priority", "Status", "Due Date", "Assigned To", "Notes"],
            "rows": [
                ["Example task", "Medium", "Not Started", "", "", ""],
            ]
        },
        "blank": {
            "headers": [],
            "rows": []
        }
    }

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        path = os.path.expanduser(params["path"])
        headers = params.get("headers", [])
        rows = params.get("rows", [])
        template = params.get("template", "blank")

        try:
            # Ensure .csv extension
            if not path.lower().endswith('.csv'):
                path = path + '.csv'

            filepath = Path(path)

            # Create parent directories if needed
            filepath.parent.mkdir(parents=True, exist_ok=True)

            # Get template if specified and no custom headers/rows
            if template != "blank" and not headers:
                template_data = self.TEMPLATES.get(template, self.TEMPLATES["blank"])
                headers = template_data["headers"]
                if not rows:
                    rows = template_data["rows"]

            # Write CSV file
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                if headers:
                    writer.writerow(headers)

                for row in rows:
                    writer.writerow(row)

            return ToolResult(
                success=True,
                data={
                    "path": str(filepath),
                    "headers": headers,
                    "row_count": len(rows),
                    "template": template,
                    "message": f"Created spreadsheet: {filepath.name}"
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e), error_type=type(e).__name__)


@register_tool
class FileCopyTool(BaseTool):
    """Copy files or directories."""

    @property
    def manifest(self) -> ToolManifest:
        return ToolManifest(
            name="filesystem.copy",
            description="Copy files or directories",
            category=ToolCategory.FILESYSTEM,
            icon="📋",
            parameters=[
                ToolParameter(
                    name="source",
                    type="string",
                    description="Source path",
                    required=True
                ),
                ToolParameter(
                    name="destination",
                    type="string",
                    description="Destination path",
                    required=True
                ),
                ToolParameter(
                    name="overwrite",
                    type="bool",
                    description="Overwrite existing files",
                    required=False,
                    default=False
                )
            ],
            permissions=["filesystem:read", "filesystem:write"],
            risk_level=RiskLevel.LOW
        )

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        source = os.path.expanduser(params["source"])
        destination = os.path.expanduser(params["destination"])
        overwrite = params.get("overwrite", False)

        try:
            src_path = Path(source)
            dst_path = Path(destination)

            if not src_path.exists():
                return ToolResult(success=False, error=f"Source not found: {source}")

            if dst_path.exists() and not overwrite:
                return ToolResult(success=False, error=f"Destination exists: {destination}")

            # Create destination parent if needed
            dst_path.parent.mkdir(parents=True, exist_ok=True)

            if src_path.is_dir():
                shutil.copytree(str(src_path), str(dst_path), dirs_exist_ok=overwrite)
            else:
                shutil.copy2(str(src_path), str(dst_path))

            return ToolResult(
                success=True,
                data={
                    "source": str(src_path),
                    "destination": str(dst_path),
                    "is_directory": src_path.is_dir()
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e), error_type=type(e).__name__)


@register_tool
class FileInfoTool(BaseTool):
    """Get detailed information about a file or directory."""

    @property
    def manifest(self) -> ToolManifest:
        return ToolManifest(
            name="filesystem.info",
            description="Get detailed information about a file or directory",
            category=ToolCategory.FILESYSTEM,
            icon="ℹ️",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the file or directory",
                    required=True
                )
            ],
            permissions=["filesystem:read"],
            risk_level=RiskLevel.LOW
        )

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        path = os.path.expanduser(params["path"])

        try:
            target = Path(path)

            if not target.exists():
                return ToolResult(success=False, error=f"Path not found: {path}")

            stat = target.stat()

            info = {
                "name": target.name,
                "path": str(target.absolute()),
                "exists": True,
                "is_file": target.is_file(),
                "is_directory": target.is_dir(),
                "is_symlink": target.is_symlink(),
                "size_bytes": stat.st_size,
                "size_human": self._human_readable_size(stat.st_size),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "accessed": datetime.fromtimestamp(stat.st_atime).isoformat(),
                "permissions": oct(stat.st_mode)[-3:],
                "extension": target.suffix if target.is_file() else None,
            }

            # Add directory-specific info
            if target.is_dir():
                items = list(target.iterdir())
                info["item_count"] = len(items)
                info["file_count"] = sum(1 for i in items if i.is_file())
                info["dir_count"] = sum(1 for i in items if i.is_dir())

            return ToolResult(
                success=True,
                data=info
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e), error_type=type(e).__name__)

    def _human_readable_size(self, size: int) -> str:
        """Convert bytes to human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"
