"""
Permission Manager for EmberOS tools.
"""

from __future__ import annotations

import fnmatch
import logging
import os
from pathlib import Path
from typing import Any

from emberos.tools.base import ToolManifest, PermissionLevel
from emberos.core.config import EmberConfig

logger = logging.getLogger(__name__)


class PermissionManager:
    """
    Manages permissions for tool execution.

    Enforces:
    - Path access restrictions
    - Operation confirmations
    - Resource limits
    """

    def __init__(self, config: EmberConfig = None):
        self.config = config or EmberConfig.from_env()
        self._permission_cache: dict[str, bool] = {}

    def check(self, manifest: ToolManifest, params: dict[str, Any]) -> bool:
        """
        Check if tool execution is permitted.

        Args:
            manifest: Tool manifest
            params: Execution parameters

        Returns:
            True if permitted, False otherwise
        """
        # Check required permissions
        for permission in manifest.permissions:
            if not self._check_permission(permission, params):
                logger.warning(f"Permission denied: {permission}")
                return False

        return True

    def _check_permission(self, permission: str, params: dict[str, Any]) -> bool:
        """Check a specific permission."""
        parts = permission.split(":")
        if len(parts) != 2:
            return True

        category, action = parts

        if category == "filesystem":
            return self._check_filesystem_permission(action, params)
        elif category == "network":
            return self._check_network_permission(action, params)
        elif category == "system":
            return self._check_system_permission(action, params)

        return True

    def _check_filesystem_permission(self, action: str, params: dict[str, Any]) -> bool:
        """Check filesystem permission."""
        perms = self.config.permissions

        # Get path from params
        path = params.get("path") or params.get("source") or params.get("file")
        if not path:
            return True

        # Expand user and resolve path
        path = os.path.expanduser(str(path))
        path = os.path.abspath(path)

        if action == "read":
            # Check against allowed paths
            if not self._path_matches_any(path, perms.filesystem_read_allowed):
                return False

            # Check against blocked paths
            if self._path_matches_any(path, perms.filesystem_read_blocked):
                return False

        elif action == "write":
            # Check against allowed paths
            if not self._path_matches_any(path, perms.filesystem_write_allowed):
                return False

            # Check file size if applicable
            if "content" in params:
                content_size = len(params["content"]) if isinstance(params["content"], (str, bytes)) else 0
                if content_size > perms.max_file_size_mb * 1024 * 1024:
                    return False

        return True

    def _check_network_permission(self, action: str, params: dict[str, Any]) -> bool:
        """Check network permission."""
        perms = self.config.permissions

        # Network disabled by default
        if not perms.network_enabled:
            return False

        # Check allowed hosts
        host = params.get("host") or params.get("url")
        if host and perms.allowed_hosts:
            if not any(fnmatch.fnmatch(host, pattern) for pattern in perms.allowed_hosts):
                return False

        return True

    def _check_system_permission(self, action: str, params: dict[str, Any]) -> bool:
        """Check system permission."""
        # System actions generally require confirmation
        # This is handled at a higher level
        return True

    def _path_matches_any(self, path: str, patterns: list[str]) -> bool:
        """Check if path matches any pattern."""
        for pattern in patterns:
            # Expand user in pattern
            expanded_pattern = os.path.expanduser(pattern)

            if fnmatch.fnmatch(path, expanded_pattern):
                return True

            # Also check if path is under the pattern directory
            if pattern.endswith("/*"):
                dir_pattern = expanded_pattern[:-2]
                if path.startswith(dir_pattern):
                    return True

        return False

    def requires_confirmation(self, manifest: ToolManifest, params: dict[str, Any]) -> bool:
        """
        Check if tool execution requires user confirmation.

        Args:
            manifest: Tool manifest
            params: Execution parameters

        Returns:
            True if confirmation required
        """
        # Check manifest setting
        if manifest.requires_confirmation:
            return True

        # Check for destructive operations
        if self.config.permissions.require_confirmation_destructive:
            destructive_tools = [
                "filesystem.delete",
                "filesystem.move",
                "system.shutdown",
                "system.restart",
            ]
            if manifest.name in destructive_tools:
                return True

        return False

    def get_confirmation_message(self, manifest: ToolManifest, params: dict[str, Any]) -> str:
        """Generate confirmation message for an operation."""
        if manifest.confirmation_message:
            # Format message with params
            try:
                return manifest.confirmation_message.format(**params)
            except KeyError:
                return manifest.confirmation_message

        return f"Execute {manifest.name}?"

    def grant_temporary(self, permission: str, duration: int = 300) -> None:
        """Grant a temporary permission (for confirmed actions)."""
        import time
        self._permission_cache[permission] = time.time() + duration

    def revoke_temporary(self, permission: str) -> None:
        """Revoke a temporary permission."""
        if permission in self._permission_cache:
            del self._permission_cache[permission]

