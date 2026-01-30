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
from typing import Any, Optional, Dict, List, Tuple
from datetime import datetime

from emberos.tools.base import (
    BaseTool, ToolResult, ToolManifest, ToolParameter,
    ToolCategory, RiskLevel
)
from emberos.tools.registry import register_tool


# =============================================================================
# FILE TYPE CLASSIFICATION SYSTEM
# =============================================================================

class FileTypeClassifier:
    """Classify files by their extension and category."""

    # Comprehensive file type mappings
    DOCUMENTS = {
        '.pdf': 'PDF Document',
        '.doc': 'Word Document (Legacy)',
        '.docx': 'Word Document',
        '.txt': 'Plain Text',
        '.md': 'Markdown',
        '.odt': 'OpenDocument Text',
        '.rtf': 'Rich Text Format',
        '.wpd': 'WordPerfect Document',
        '.xps': 'XPS Document',
        '.pages': 'Apple Pages',
        '.tex': 'LaTeX Document',
        '.bib': 'BibTeX Bibliography',
        '.epub': 'E-Book',
        '.gdoc': 'Google Doc',
    }

    SPREADSHEETS = {
        '.xls': 'Excel Spreadsheet (Legacy)',
        '.xlsx': 'Excel Spreadsheet',
        '.ods': 'OpenDocument Spreadsheet',
        '.csv': 'CSV Data',
        '.tsv': 'TSV Data',
    }

    CODE_FILES = {
        '.py': 'Python',
        '.js': 'JavaScript',
        '.ts': 'TypeScript',
        '.java': 'Java',
        '.cpp': 'C++',
        '.c': 'C',
        '.h': 'C/C++ Header',
        '.hpp': 'C++ Header',
        '.rs': 'Rust',
        '.go': 'Go',
        '.rb': 'Ruby',
        '.php': 'PHP',
        '.swift': 'Swift',
        '.kt': 'Kotlin',
        '.scala': 'Scala',
        '.cs': 'C#',
        '.sh': 'Shell Script',
        '.bash': 'Bash Script',
        '.ps1': 'PowerShell',
        '.sql': 'SQL',
        '.r': 'R',
        '.lua': 'Lua',
        '.pl': 'Perl',
    }

    PRESENTATIONS = {
        '.ppt': 'PowerPoint (Legacy)',
        '.pptx': 'PowerPoint Presentation',
        '.odp': 'OpenDocument Presentation',
        '.key': 'Apple Keynote',
    }

    IMAGES = {
        '.jpg': 'JPEG Image',
        '.jpeg': 'JPEG Image',
        '.png': 'PNG Image',
        '.gif': 'GIF Image',
        '.bmp': 'Bitmap Image',
        '.tiff': 'TIFF Image',
        '.svg': 'SVG Vector',
        '.webp': 'WebP Image',
        '.ico': 'Icon',
        '.raw': 'RAW Image',
    }

    DATA_FILES = {
        '.json': 'JSON Data',
        '.xml': 'XML Data',
        '.yaml': 'YAML Data',
        '.yml': 'YAML Data',
        '.toml': 'TOML Config',
        '.ini': 'INI Config',
        '.cfg': 'Config File',
    }

    WEB_FILES = {
        '.html': 'HTML Document',
        '.htm': 'HTML Document',
        '.css': 'CSS Stylesheet',
        '.scss': 'SCSS Stylesheet',
        '.less': 'LESS Stylesheet',
    }

    ARCHIVES = {
        '.zip': 'ZIP Archive',
        '.tar': 'TAR Archive',
        '.gz': 'GZip Archive',
        '.rar': 'RAR Archive',
        '.7z': '7-Zip Archive',
        '.bz2': 'BZip2 Archive',
    }

    @classmethod
    def classify(cls, extension: str) -> Tuple[str, str]:
        """
        Classify a file by extension.

        Returns:
            Tuple of (category, description)
        """
        ext = extension.lower() if extension.startswith('.') else f'.{extension.lower()}'

        if ext in cls.DOCUMENTS:
            return ('document', cls.DOCUMENTS[ext])
        elif ext in cls.SPREADSHEETS:
            return ('spreadsheet', cls.SPREADSHEETS[ext])
        elif ext in cls.CODE_FILES:
            return ('code', cls.CODE_FILES[ext])
        elif ext in cls.PRESENTATIONS:
            return ('presentation', cls.PRESENTATIONS[ext])
        elif ext in cls.IMAGES:
            return ('image', cls.IMAGES[ext])
        elif ext in cls.DATA_FILES:
            return ('data', cls.DATA_FILES[ext])
        elif ext in cls.WEB_FILES:
            return ('web', cls.WEB_FILES[ext])
        elif ext in cls.ARCHIVES:
            return ('archive', cls.ARCHIVES[ext])
        else:
            return ('other', 'Unknown File Type')

    @classmethod
    def is_creatable(cls, extension: str) -> bool:
        """Check if a file type can be created."""
        ext = extension.lower() if extension.startswith('.') else f'.{extension.lower()}'

        # Creatable document types
        creatable = {
            '.pdf', '.doc', '.docx', '.txt', '.md', '.odt', '.rtf',
            '.xls', '.xlsx', '.csv', '.ods',
            '.py', '.js', '.java', '.cpp', '.c', '.h', '.rs', '.go',
            '.pptx', '.odp',
            '.html', '.htm', '.xml', '.json', '.yaml', '.yml',
        }
        return ext in creatable

    @classmethod
    def is_readable(cls, extension: str) -> bool:
        """Check if a file type can be read/parsed."""
        ext = extension.lower() if extension.startswith('.') else f'.{extension.lower()}'

        # All categorized types are readable
        all_types = set()
        for type_dict in [cls.DOCUMENTS, cls.SPREADSHEETS, cls.CODE_FILES,
                          cls.PRESENTATIONS, cls.IMAGES, cls.DATA_FILES,
                          cls.WEB_FILES]:
            all_types.update(type_dict.keys())

        return ext in all_types


# =============================================================================
# PATH UTILITIES AND ALIASES
# =============================================================================

class PathResolver:
    """Resolve path aliases and normalize paths safely."""

    # Common folder aliases (case-insensitive)
    ALIASES = {
        'downloads': '~/Downloads',
        'download': '~/Downloads',
        'documents': '~/Documents',
        'document': '~/Documents',
        'docs': '~/Documents',
        'desktop': '~/Desktop',
        'pictures': '~/Pictures',
        'photos': '~/Pictures',
        'images': '~/Pictures',
        'videos': '~/Videos',
        'video': '~/Videos',
        'music': '~/Music',
        'audio': '~/Music',
        'home': '~',
        'tmp': '/tmp',
        'temp': '/tmp',
    }

    # Platform-specific adjustments
    if os.name == 'nt':  # Windows
        ALIASES.update({
            'tmp': os.path.expandvars('%TEMP%'),
            'temp': os.path.expandvars('%TEMP%'),
            'appdata': os.path.expandvars('%APPDATA%'),
            'localappdata': os.path.expandvars('%LOCALAPPDATA%'),
        })

    @classmethod
    def resolve(cls, path_or_alias: str, base_dir: Optional[str] = None) -> Path:
        """
        Resolve a path or alias to an absolute Path.

        Args:
            path_or_alias: A path string or alias like 'downloads'
            base_dir: Base directory for relative paths

        Returns:
            Resolved absolute Path
        """
        path_str = path_or_alias.strip()

        # Check if it's an alias (case-insensitive)
        alias_key = path_str.lower().strip()
        if alias_key in cls.ALIASES:
            path_str = cls.ALIASES[alias_key]

        # Expand user home
        path_str = os.path.expanduser(path_str)

        # Expand environment variables
        path_str = os.path.expandvars(path_str)

        # Convert to Path
        path = Path(path_str)

        # Make absolute relative to base_dir if provided
        if not path.is_absolute():
            if base_dir:
                path = Path(base_dir) / path
            else:
                path = Path.cwd() / path

        # Resolve to canonical path (but don't follow symlinks outside allowed areas)
        try:
            path = path.resolve()
        except OSError:
            pass

        return path

    @classmethod
    def is_safe_path(cls, path: Path, allow_system: bool = False) -> bool:
        """
        Check if a path is safe to access.

        Blocks access to system directories unless explicitly allowed.
        """
        path_str = str(path).lower()

        # Blocked paths (never allow)
        blocked_patterns = [
            '/etc', '/boot', '/sys', '/proc', '/dev',
            'c:\\windows', 'c:\\program files', 'c:\\programdata',
            '/root', '/var/log', '/var/run',
        ]

        if not allow_system:
            for blocked in blocked_patterns:
                if path_str.startswith(blocked):
                    return False

        return True

    @classmethod
    def find_similar_folders(cls, target_name: str, search_in: Path) -> List[str]:
        """
        Find folders with similar names (for suggestions).
        """
        similar = []
        target_lower = target_name.lower()

        try:
            for item in search_in.iterdir():
                if item.is_dir():
                    name_lower = item.name.lower()
                    # Check for similar names (contains, prefix, suffix)
                    if target_lower in name_lower or name_lower in target_lower:
                        similar.append(item.name)
                    # Check for common typos (first letter match)
                    elif name_lower[0] == target_lower[0]:
                        similar.append(item.name)
        except PermissionError:
            pass

        return similar[:5]  # Limit suggestions


# =============================================================================
# PAGINATION STATE MANAGER
# =============================================================================

class PaginationState:
    """Manage pagination state for directory listings."""

    # Global state storage (thread-safe for async)
    _states: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def create(cls, session_id: str, path: str, all_items: List[dict], page_size: int = 10) -> str:
        """
        Create a new pagination state.

        Returns:
            Session ID for this pagination
        """
        cls._states[session_id] = {
            'path': path,
            'items': all_items,
            'page_size': page_size,
            'current_index': 0,
            'created_at': datetime.now().isoformat()
        }
        return session_id

    @classmethod
    def get_page(cls, session_id: str, page_size: Optional[int] = None) -> Tuple[List[dict], bool, int, int]:
        """
        Get the next page of items.

        Returns:
            Tuple of (items, has_more, shown_count, total_count)
        """
        if session_id not in cls._states:
            return [], False, 0, 0

        state = cls._states[session_id]
        items = state['items']
        size = page_size or state['page_size']
        idx = state['current_index']

        page_items = items[idx:idx + size]
        state['current_index'] = idx + len(page_items)

        has_more = state['current_index'] < len(items)
        shown_count = state['current_index']
        total_count = len(items)

        return page_items, has_more, shown_count, total_count

    @classmethod
    def reset(cls, session_id: str) -> None:
        """Reset pagination to the beginning."""
        if session_id in cls._states:
            cls._states[session_id]['current_index'] = 0

    @classmethod
    def clear(cls, session_id: str) -> None:
        """Clear pagination state."""
        if session_id in cls._states:
            del cls._states[session_id]

    @classmethod
    def cleanup_old(cls, max_age_seconds: int = 3600) -> None:
        """Clean up old pagination states."""
        now = datetime.now()
        to_remove = []

        for sid, state in cls._states.items():
            created = datetime.fromisoformat(state['created_at'])
            age = (now - created).total_seconds()
            if age > max_age_seconds:
                to_remove.append(sid)

        for sid in to_remove:
            del cls._states[sid]


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
                ),
                ToolParameter(
                    name="max_items",
                    type="int",
                    description="Maximum number of items to return",
                    required=False,
                    default=20
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
        max_items = params.get("max_items", 20)

        try:
            directory = Path(path)

            if not directory.exists():
                return ToolResult(success=False, error=f"Directory not found: {path}")

            if not directory.is_dir():
                return ToolResult(success=False, error=f"Not a directory: {path}")

            all_items = self._list_dir(directory, recursive, show_hidden, max_depth, 0)

            # Limit items and add truncation notice
            total_count = len(all_items)
            items = all_items[:max_items]
            truncated = total_count > max_items

            result_data = {
                "path": str(directory),
                "items": items,
                "count": len(items),
                "total_count": total_count,
                "truncated": truncated
            }

            if truncated:
                result_data["message"] = f"Showing first {max_items} of {total_count} items. Set max_items parameter to see more."

            return ToolResult(
                success=True,
                data=result_data
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


# =============================================================================
# ENHANCED DIRECTORY LISTING WITH PAGINATION
# =============================================================================

@register_tool
class EnhancedDirectoryListTool(BaseTool):
    """
    Enhanced directory listing with pagination, smart path resolution,
    and comprehensive file type detection.
    """

    @property
    def manifest(self) -> ToolManifest:
        return ToolManifest(
            name="filesystem.list_enhanced",
            description="List directory contents with pagination, smart path resolution, and file type classification",
            category=ToolCategory.FILESYSTEM,
            icon="📂",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Directory path or alias (e.g., 'downloads', 'documents', '~/Projects')",
                    required=True
                ),
                ToolParameter(
                    name="page_size",
                    type="int",
                    description="Number of items per page (default 10)",
                    required=False,
                    default=10
                ),
                ToolParameter(
                    name="continue_pagination",
                    type="bool",
                    description="Continue from previous pagination state",
                    required=False,
                    default=False
                ),
                ToolParameter(
                    name="session_id",
                    type="string",
                    description="Pagination session ID (for continuing)",
                    required=False
                ),
                ToolParameter(
                    name="show_hidden",
                    type="bool",
                    description="Show hidden files",
                    required=False,
                    default=False
                ),
                ToolParameter(
                    name="sort_by",
                    type="string",
                    description="Sort by: 'name', 'size', 'modified', 'type'",
                    required=False,
                    default="name",
                    choices=["name", "size", "modified", "type"]
                ),
                ToolParameter(
                    name="sort_order",
                    type="string",
                    description="Sort order: 'asc' or 'desc'",
                    required=False,
                    default="asc",
                    choices=["asc", "desc"]
                )
            ],
            permissions=["filesystem:read"],
            risk_level=RiskLevel.LOW
        )

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        path_input = params["path"]
        page_size = params.get("page_size", 10)
        continue_pagination = params.get("continue_pagination", False)
        session_id = params.get("session_id")
        show_hidden = params.get("show_hidden", False)
        sort_by = params.get("sort_by", "name")
        sort_order = params.get("sort_order", "asc")

        try:
            # Handle pagination continuation
            if continue_pagination and session_id:
                return await self._continue_pagination(session_id, page_size)

            # Resolve path using aliases
            directory = PathResolver.resolve(path_input)

            # Check if path is safe
            if not PathResolver.is_safe_path(directory):
                return ToolResult(
                    success=False,
                    error=f"Access denied: Cannot list system directory '{directory}'"
                )

            # Handle non-existent directory with suggestions
            if not directory.exists():
                return await self._handle_missing_directory(path_input, directory)

            if not directory.is_dir():
                return ToolResult(
                    success=False,
                    error=f"Not a directory: {directory}"
                )

            # Check read permission
            try:
                list(directory.iterdir())
            except PermissionError:
                return ToolResult(
                    success=False,
                    error=f"Permission denied: Cannot read directory '{directory}'"
                )

            # Get all items with full info
            all_items = await self._get_directory_items(directory, show_hidden)

            # Handle empty directory
            if not all_items:
                return ToolResult(
                    success=True,
                    data={
                        "path": str(directory),
                        "items": [],
                        "count": 0,
                        "total_count": 0,
                        "is_empty": True,
                        "message": f"Directory '{directory.name}' is empty"
                    }
                )

            # Sort items (folders first, then by specified criteria)
            all_items = self._sort_items(all_items, sort_by, sort_order)

            # Create pagination session
            import hashlib
            new_session_id = hashlib.md5(f"{directory}{datetime.now().timestamp()}".encode()).hexdigest()[:12]
            PaginationState.create(new_session_id, str(directory), all_items, page_size)

            # Get first page
            page_items, has_more, shown, total = PaginationState.get_page(new_session_id, page_size)

            result_data = {
                "path": str(directory),
                "display_path": self._display_path(directory),
                "items": page_items,
                "count": len(page_items),
                "total_count": total,
                "shown_count": shown,
                "has_more": has_more,
                "page_size": page_size,
                "session_id": new_session_id if has_more else None
            }

            if has_more:
                remaining = total - shown
                result_data["message"] = f"Showing {shown} of {total} items. {remaining} more available. Reply 'show more' or 'list more' to continue."
                result_data["prompt_continue"] = True

            return ToolResult(success=True, data=result_data)

        except Exception as e:
            return ToolResult(success=False, error=str(e), error_type=type(e).__name__)

    async def _continue_pagination(self, session_id: str, page_size: int) -> ToolResult:
        """Continue pagination from previous state."""
        page_items, has_more, shown, total = PaginationState.get_page(session_id, page_size)

        if not page_items:
            return ToolResult(
                success=True,
                data={
                    "message": "No more items to show or pagination session expired.",
                    "items": [],
                    "count": 0
                }
            )

        result_data = {
            "items": page_items,
            "count": len(page_items),
            "total_count": total,
            "shown_count": shown,
            "has_more": has_more,
            "session_id": session_id if has_more else None
        }

        if has_more:
            remaining = total - shown
            result_data["message"] = f"Showing items {shown - len(page_items) + 1} to {shown} of {total}. {remaining} more available."
            result_data["prompt_continue"] = True
        else:
            result_data["message"] = f"Showing items {shown - len(page_items) + 1} to {shown}. End of listing."
            PaginationState.clear(session_id)

        return ToolResult(success=True, data=result_data)

    async def _handle_missing_directory(self, path_input: str, directory: Path) -> ToolResult:
        """Handle missing directory with helpful suggestions."""
        # Find the nearest existing parent
        parent = directory.parent
        while not parent.exists() and parent != parent.parent:
            parent = parent.parent

        suggestions = []
        if parent.exists():
            suggestions = PathResolver.find_similar_folders(directory.name, parent)

            # List actual sibling directories
            try:
                siblings = [d.name for d in parent.iterdir() if d.is_dir() and not d.name.startswith('.')][:10]
            except PermissionError:
                siblings = []
        else:
            siblings = []

        error_msg = f"Directory not found: '{path_input}'"
        if suggestions:
            error_msg += f"\n\nDid you mean: {', '.join(suggestions)}?"
        if siblings:
            error_msg += f"\n\nExisting folders in '{parent}': {', '.join(siblings)}"

        return ToolResult(
            success=False,
            error=error_msg,
            data={
                "requested_path": str(directory),
                "parent_path": str(parent),
                "suggestions": suggestions,
                "existing_folders": siblings
            }
        )

    async def _get_directory_items(self, directory: Path, show_hidden: bool) -> List[dict]:
        """Get all items in directory with full information."""
        items = []

        for item in directory.iterdir():
            if not show_hidden and item.name.startswith('.'):
                continue

            try:
                stat = item.stat()

                # Classify file type
                if item.is_dir():
                    category, type_desc = 'folder', 'Folder'
                else:
                    category, type_desc = FileTypeClassifier.classify(item.suffix)

                entry = {
                    "name": item.name,
                    "path": str(item),
                    "is_dir": item.is_dir(),
                    "is_file": item.is_file(),
                    "is_symlink": item.is_symlink(),
                    "size": stat.st_size,
                    "size_human": self._human_readable_size(stat.st_size),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "modified_display": self._format_modified_time(stat.st_mtime),
                    "extension": item.suffix.lower() if item.is_file() else None,
                    "category": category,
                    "type_description": type_desc
                }
                items.append(entry)

            except (PermissionError, OSError) as e:
                # Include inaccessible items with error marker
                items.append({
                    "name": item.name,
                    "path": str(item),
                    "is_dir": item.is_dir(),
                    "error": str(e),
                    "accessible": False
                })

        return items

    def _sort_items(self, items: List[dict], sort_by: str, sort_order: str) -> List[dict]:
        """Sort items with folders first."""
        # Separate folders and files
        folders = [i for i in items if i.get("is_dir", False)]
        files = [i for i in items if not i.get("is_dir", False)]

        # Sort key function
        def get_sort_key(item):
            if sort_by == "name":
                return item.get("name", "").lower()
            elif sort_by == "size":
                return item.get("size", 0)
            elif sort_by == "modified":
                return item.get("modified", "")
            elif sort_by == "type":
                return (item.get("category", "zzz"), item.get("name", "").lower())
            return item.get("name", "").lower()

        reverse = (sort_order == "desc")

        folders.sort(key=get_sort_key, reverse=reverse)
        files.sort(key=get_sort_key, reverse=reverse)

        # Folders first, then files
        return folders + files

    def _human_readable_size(self, size: int) -> str:
        """Convert bytes to human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    def _format_modified_time(self, mtime: float) -> str:
        """Format modification time in human-friendly way."""
        dt = datetime.fromtimestamp(mtime)
        now = datetime.now()
        diff = now - dt

        if diff.days == 0:
            if diff.seconds < 60:
                return "just now"
            elif diff.seconds < 3600:
                mins = diff.seconds // 60
                return f"{mins} minute{'s' if mins > 1 else ''} ago"
            else:
                hours = diff.seconds // 3600
                return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.days == 1:
            return "yesterday"
        elif diff.days < 7:
            return f"{diff.days} days ago"
        else:
            return dt.strftime("%Y-%m-%d")

    def _display_path(self, path: Path) -> str:
        """Format path for display (abbreviate home)."""
        home = Path.home()
        try:
            relative = path.relative_to(home)
            return f"~/{relative}"
        except ValueError:
            return str(path)


# =============================================================================
# ADVANCED FILE SEARCH
# =============================================================================

@register_tool
class AdvancedFileSearchTool(BaseTool):
    """
    Advanced file search with multiple match modes, file type filtering,
    and comprehensive result formatting.
    """

    @property
    def manifest(self) -> ToolManifest:
        return ToolManifest(
            name="filesystem.find",
            description="Find files by name with exact/partial/fuzzy matching and file type filtering",
            category=ToolCategory.FILESYSTEM,
            icon="🔍",
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="File name to search for (supports wildcards)",
                    required=True
                ),
                ToolParameter(
                    name="path",
                    type="string",
                    description="Directory to search in (default: home)",
                    required=False,
                    default="~"
                ),
                ToolParameter(
                    name="file_type",
                    type="string",
                    description="Filter by type: 'document', 'spreadsheet', 'code', 'image', 'all'",
                    required=False,
                    default="all",
                    choices=["document", "spreadsheet", "code", "image", "presentation", "data", "archive", "all"]
                ),
                ToolParameter(
                    name="match_mode",
                    type="string",
                    description="Match mode: 'exact', 'partial', 'wildcard'",
                    required=False,
                    default="partial",
                    choices=["exact", "partial", "wildcard"]
                ),
                ToolParameter(
                    name="case_sensitive",
                    type="bool",
                    description="Case-sensitive search",
                    required=False,
                    default=False
                ),
                ToolParameter(
                    name="max_results",
                    type="int",
                    description="Maximum number of results",
                    required=False,
                    default=20
                ),
                ToolParameter(
                    name="max_depth",
                    type="int",
                    description="Maximum directory depth to search",
                    required=False,
                    default=5
                )
            ],
            permissions=["filesystem:read"],
            risk_level=RiskLevel.LOW
        )

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        query = params["query"]
        path_input = params.get("path", "~")
        file_type = params.get("file_type", "all")
        match_mode = params.get("match_mode", "partial")
        case_sensitive = params.get("case_sensitive", False)
        max_results = params.get("max_results", 20)
        max_depth = params.get("max_depth", 5)

        try:
            # Resolve search directory
            search_dir = PathResolver.resolve(path_input)

            if not search_dir.exists():
                return ToolResult(
                    success=False,
                    error=f"Search directory not found: {path_input}"
                )

            if not PathResolver.is_safe_path(search_dir):
                return ToolResult(
                    success=False,
                    error=f"Access denied: Cannot search system directory"
                )

            # Get file type filter extensions
            type_extensions = self._get_type_extensions(file_type)

            # Perform search
            results = []
            search_query = query if case_sensitive else query.lower()

            for match in self._recursive_search(
                search_dir, search_query, match_mode, case_sensitive,
                type_extensions, max_depth, 0
            ):
                if len(results) >= max_results:
                    break
                results.append(match)

            # Format results
            if len(results) == 0:
                return ToolResult(
                    success=True,
                    data={
                        "query": query,
                        "search_path": str(search_dir),
                        "results": [],
                        "count": 0,
                        "message": f"No files matching '{query}' found in {search_dir}"
                    }
                )

            if len(results) == 1:
                # Single result - provide full details
                return ToolResult(
                    success=True,
                    data={
                        "query": query,
                        "search_path": str(search_dir),
                        "results": results,
                        "count": 1,
                        "single_match": True,
                        "match": results[0],
                        "message": f"Found: {results[0]['path']}"
                    }
                )

            # Multiple results
            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "search_path": str(search_dir),
                    "results": results,
                    "count": len(results),
                    "multiple_matches": True,
                    "message": f"Found {len(results)} files matching '{query}'. Please specify which one."
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e), error_type=type(e).__name__)

    def _get_type_extensions(self, file_type: str) -> Optional[set]:
        """Get file extensions for a type category."""
        if file_type == "all":
            return None

        type_map = {
            "document": set(FileTypeClassifier.DOCUMENTS.keys()),
            "spreadsheet": set(FileTypeClassifier.SPREADSHEETS.keys()),
            "code": set(FileTypeClassifier.CODE_FILES.keys()),
            "image": set(FileTypeClassifier.IMAGES.keys()),
            "presentation": set(FileTypeClassifier.PRESENTATIONS.keys()),
            "data": set(FileTypeClassifier.DATA_FILES.keys()),
            "archive": set(FileTypeClassifier.ARCHIVES.keys()),
        }

        return type_map.get(file_type)

    def _recursive_search(
        self,
        directory: Path,
        query: str,
        match_mode: str,
        case_sensitive: bool,
        type_extensions: Optional[set],
        max_depth: int,
        current_depth: int
    ) -> List[dict]:
        """Recursively search for files."""
        results = []

        if current_depth > max_depth:
            return results

        try:
            for item in directory.iterdir():
                # Skip hidden files/directories
                if item.name.startswith('.'):
                    continue

                if item.is_dir():
                    # Recurse into subdirectories
                    results.extend(self._recursive_search(
                        item, query, match_mode, case_sensitive,
                        type_extensions, max_depth, current_depth + 1
                    ))
                elif item.is_file():
                    # Check extension filter
                    if type_extensions and item.suffix.lower() not in type_extensions:
                        continue

                    # Check name match
                    name = item.name if case_sensitive else item.name.lower()

                    if self._matches(name, query, match_mode):
                        stat = item.stat()
                        category, type_desc = FileTypeClassifier.classify(item.suffix)

                        results.append({
                            "name": item.name,
                            "path": str(item),
                            "directory": str(item.parent),
                            "size": stat.st_size,
                            "size_human": self._human_readable_size(stat.st_size),
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            "extension": item.suffix.lower(),
                            "category": category,
                            "type_description": type_desc
                        })

        except PermissionError:
            pass

        return results

    def _matches(self, name: str, query: str, mode: str) -> bool:
        """Check if name matches query based on mode."""
        if mode == "exact":
            return name == query
        elif mode == "partial":
            return query in name
        elif mode == "wildcard":
            return fnmatch.fnmatch(name, query)
        return False

    def _human_readable_size(self, size: int) -> str:
        """Convert bytes to human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"


# =============================================================================
# FILE CREATION TOOL
# =============================================================================

@register_tool
class CreateFileTool(BaseTool):
    """
    Create various types of files with content or from templates.
    """

    @property
    def manifest(self) -> ToolManifest:
        return ToolManifest(
            name="filesystem.create_file",
            description="Create a new file with content (supports txt, md, py, js, etc.)",
            category=ToolCategory.FILESYSTEM,
            icon="📝",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path for the new file (include extension)",
                    required=True
                ),
                ToolParameter(
                    name="content",
                    type="string",
                    description="Content to write to the file",
                    required=False,
                    default=""
                ),
                ToolParameter(
                    name="template",
                    type="string",
                    description="Template type: 'python', 'javascript', 'html', 'markdown', 'readme', 'blank'",
                    required=False,
                    default="blank",
                    choices=["python", "javascript", "html", "markdown", "readme", "json", "yaml", "blank"]
                ),
                ToolParameter(
                    name="overwrite",
                    type="bool",
                    description="Overwrite if file exists",
                    required=False,
                    default=False
                )
            ],
            permissions=["filesystem:write"],
            risk_level=RiskLevel.LOW,
            requires_confirmation=False
        )

    # File templates
    TEMPLATES = {
        "python": '''#!/usr/bin/env python3
"""
{title}

Created: {date}
"""

def main():
    """Main function."""
    pass


if __name__ == "__main__":
    main()
''',
        "javascript": '''/**
 * {title}
 * Created: {date}
 */

function main() {{
    // Your code here
}}

main();
''',
        "html": '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p>Content goes here.</p>
</body>
</html>
''',
        "markdown": '''# {title}

Created: {date}

## Introduction

Your content here.

## Section 1

### Subsection 1.1

Content...
''',
        "readme": '''# {title}

## Description

A brief description of this project.

## Installation

```bash
# Installation steps
```

## Usage

```bash
# Usage examples
```

## License

MIT
''',
        "json": '''{{
    "name": "{title}",
    "version": "1.0.0",
    "description": "",
    "created": "{date}"
}}
''',
        "yaml": '''# {title}
# Created: {date}

name: "{title}"
version: "1.0.0"
description: ""
''',
        "blank": ""
    }

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        path_input = params["path"]
        content = params.get("content", "")
        template = params.get("template", "blank")
        overwrite = params.get("overwrite", False)

        try:
            # Resolve path
            filepath = PathResolver.resolve(path_input)

            # Check if file type is creatable
            ext = filepath.suffix.lower()
            if ext and not FileTypeClassifier.is_creatable(ext):
                return ToolResult(
                    success=False,
                    error=f"Cannot create files of type '{ext}'. Supported types: txt, md, py, js, html, json, yaml, csv"
                )

            # Check if file exists
            if filepath.exists() and not overwrite:
                return ToolResult(
                    success=False,
                    error=f"File already exists: {filepath}. Set overwrite=true to replace."
                )

            # Create parent directories
            filepath.parent.mkdir(parents=True, exist_ok=True)

            # Determine content to write
            if content:
                final_content = content
            elif template != "blank":
                # Use template
                template_content = self.TEMPLATES.get(template, "")
                final_content = template_content.format(
                    title=filepath.stem,
                    date=datetime.now().strftime("%Y-%m-%d")
                )
            else:
                final_content = ""

            # Write file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(final_content)

            return ToolResult(
                success=True,
                data={
                    "path": str(filepath),
                    "size": len(final_content.encode('utf-8')),
                    "template_used": template if not content else None,
                    "message": f"Created file: {filepath.name}"
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e), error_type=type(e).__name__)


# =============================================================================
# FILE RENAME TOOL
# =============================================================================

@register_tool
class FileRenameTool(BaseTool):
    """Rename a file or directory."""

    @property
    def manifest(self) -> ToolManifest:
        return ToolManifest(
            name="filesystem.rename",
            description="Rename a file or directory",
            category=ToolCategory.FILESYSTEM,
            icon="✏️",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the file or directory to rename",
                    required=True
                ),
                ToolParameter(
                    name="new_name",
                    type="string",
                    description="New name (not full path, just the name)",
                    required=True
                )
            ],
            permissions=["filesystem:write"],
            risk_level=RiskLevel.MEDIUM,
            requires_confirmation=True,
            confirmation_message="Rename '{path}' to '{new_name}'?"
        )

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        path_input = params["path"]
        new_name = params["new_name"]

        try:
            # Resolve path
            source = PathResolver.resolve(path_input)

            if not source.exists():
                return ToolResult(
                    success=False,
                    error=f"File or directory not found: {path_input}"
                )

            # Create destination path (same directory, new name)
            destination = source.parent / new_name

            if destination.exists():
                return ToolResult(
                    success=False,
                    error=f"A file or directory named '{new_name}' already exists"
                )

            # Perform rename
            source.rename(destination)

            return ToolResult(
                success=True,
                data={
                    "original_path": str(source),
                    "new_path": str(destination),
                    "original_name": source.name,
                    "new_name": new_name,
                    "message": f"Renamed '{source.name}' to '{new_name}'"
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e), error_type=type(e).__name__)


# =============================================================================
# SAFE DELETE TOOL (with confirmation and rollback info)
# =============================================================================

@register_tool
class SafeDeleteTool(BaseTool):
    """
    Safe file/directory deletion with confirmation and rollback capability.
    """

    @property
    def manifest(self) -> ToolManifest:
        return ToolManifest(
            name="filesystem.safe_delete",
            description="Safely delete files or directories with confirmation and rollback support",
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
                    name="confirm",
                    type="bool",
                    description="Explicit confirmation (must be true to proceed)",
                    required=False,
                    default=False
                )
            ],
            permissions=["filesystem:write"],
            risk_level=RiskLevel.HIGH,
            requires_confirmation=True,
            confirmation_message="Are you sure you want to delete '{path}'? A snapshot will be created for rollback."
        )

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        path_input = params["path"]
        confirm = params.get("confirm", False)

        try:
            target = PathResolver.resolve(path_input)

            if not target.exists():
                return ToolResult(
                    success=False,
                    error=f"Path not found: {path_input}"
                )

            # Check safety
            if not PathResolver.is_safe_path(target):
                return ToolResult(
                    success=False,
                    error=f"Cannot delete system path: {target}"
                )

            # If not confirmed, return preview
            if not confirm:
                info = self._get_delete_info(target)
                return ToolResult(
                    success=True,
                    data={
                        "action": "preview",
                        "path": str(target),
                        "type": "directory" if target.is_dir() else "file",
                        "size": info.get("size", 0),
                        "size_human": info.get("size_human", "0 B"),
                        "item_count": info.get("item_count", 1),
                        "requires_confirmation": True,
                        "message": f"To delete '{target.name}' ({info.get('size_human', '0 B')}), confirm the action."
                    }
                )

            # Perform deletion
            was_dir = target.is_dir()

            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()

            return ToolResult(
                success=True,
                data={
                    "path": str(target),
                    "deleted": True,
                    "was_directory": was_dir,
                    "rollback_available": True,
                    "message": f"Deleted: {target.name}. Rollback is available."
                }
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e), error_type=type(e).__name__)

    def _get_delete_info(self, path: Path) -> dict:
        """Get information about what will be deleted."""
        info = {
            "path": str(path),
            "name": path.name
        }

        try:
            if path.is_file():
                stat = path.stat()
                info["size"] = stat.st_size
                info["size_human"] = self._human_readable_size(stat.st_size)
                info["item_count"] = 1
            elif path.is_dir():
                total_size = 0
                item_count = 0

                for item in path.rglob("*"):
                    item_count += 1
                    if item.is_file():
                        try:
                            total_size += item.stat().st_size
                        except OSError:
                            pass

                info["size"] = total_size
                info["size_human"] = self._human_readable_size(total_size)
                info["item_count"] = item_count + 1  # +1 for the directory itself

        except OSError:
            info["size"] = 0
            info["size_human"] = "Unknown"
            info["item_count"] = 1

        return info

    def _human_readable_size(self, size: int) -> str:
        """Convert bytes to human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"


# =============================================================================
# CHECK FILE EXISTS TOOL
# =============================================================================

@register_tool
class CheckExistsTool(BaseTool):
    """Check if a file or directory exists."""

    @property
    def manifest(self) -> ToolManifest:
        return ToolManifest(
            name="filesystem.exists",
            description="Check if a file or directory exists",
            category=ToolCategory.FILESYSTEM,
            icon="❓",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to check",
                    required=True
                )
            ],
            permissions=["filesystem:read"],
            risk_level=RiskLevel.LOW
        )

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        path_input = params["path"]

        try:
            target = PathResolver.resolve(path_input)

            exists = target.exists()

            result = {
                "path": str(target),
                "exists": exists,
            }

            if exists:
                result["is_file"] = target.is_file()
                result["is_directory"] = target.is_dir()
                result["is_symlink"] = target.is_symlink()

                if target.is_file():
                    stat = target.stat()
                    result["size"] = stat.st_size
                    result["modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()

            return ToolResult(success=True, data=result)

        except Exception as e:
            return ToolResult(success=False, error=str(e), error_type=type(e).__name__)
