"""
Base classes for EmberOS tools.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum


class ToolCategory(str, Enum):
    """Tool categories."""
    FILESYSTEM = "filesystem"
    NOTES = "notes"
    CALENDAR = "calendar"
    APPLICATIONS = "applications"
    SYSTEM = "system"
    NETWORK = "network"
    DEVELOPMENT = "development"
    CUSTOM = "custom"


class PermissionLevel(str, Enum):
    """Permission levels for tool operations."""
    NONE = "none"
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


class RiskLevel(str, Enum):
    """Risk level for tool operations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ToolParameter:
    """Definition of a tool parameter."""
    name: str
    type: str  # string, int, float, bool, list, dict
    description: str
    required: bool = True
    default: Any = None
    validation: Optional[str] = None  # Validation rule name
    choices: Optional[list] = None


@dataclass
class ToolManifest:
    """
    Manifest describing a tool's capabilities and requirements.
    """
    name: str
    description: str
    version: str = "1.0.0"
    author: str = "EmberOS"
    category: ToolCategory = ToolCategory.CUSTOM
    icon: str = "🔧"

    # Parameters
    parameters: list[ToolParameter] = field(default_factory=list)

    # Permissions
    permissions: list[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW

    # Confirmation
    requires_confirmation: bool = False
    confirmation_message: Optional[str] = None

    # Execution
    timeout: int = 60
    async_capable: bool = True

    # Hooks
    before_execute: Optional[str] = None
    after_execute: Optional[str] = None
    on_error: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        result = asdict(self)
        result["category"] = self.category.value
        result["risk_level"] = self.risk_level.value
        result["parameters"] = [asdict(p) for p in self.parameters]
        return result

    def to_schema(self) -> dict:
        """Convert to JSON schema for LLM."""
        properties = {}
        required = []

        for param in self.parameters:
            prop = {
                "type": self._type_to_json_type(param.type),
                "description": param.description
            }

            if param.choices:
                prop["enum"] = param.choices

            if param.default is not None:
                prop["default"] = param.default

            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }

    def _type_to_json_type(self, type_str: str) -> str:
        """Convert Python type to JSON schema type."""
        mapping = {
            "string": "string",
            "str": "string",
            "int": "integer",
            "integer": "integer",
            "float": "number",
            "number": "number",
            "bool": "boolean",
            "boolean": "boolean",
            "list": "array",
            "array": "array",
            "dict": "object",
            "object": "object",
        }
        return mapping.get(type_str.lower(), "string")


@dataclass
class ToolResult:
    """Result from tool execution."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    duration_ms: int = 0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class BaseTool(ABC):
    """
    Base class for all EmberOS tools.

    Tools should inherit from this class and implement:
    - manifest: Tool manifest describing capabilities
    - execute: Main execution method
    - validate: Parameter validation (optional)
    """

    @property
    @abstractmethod
    def manifest(self) -> ToolManifest:
        """Return the tool manifest."""
        pass

    @abstractmethod
    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """
        Execute the tool with given parameters.

        Args:
            params: Dictionary of parameters

        Returns:
            ToolResult with execution outcome
        """
        pass

    def validate(self, params: dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate parameters before execution.

        Args:
            params: Dictionary of parameters

        Returns:
            Tuple of (is_valid, error_message)
        """
        manifest = self.manifest

        # Check required parameters
        for param in manifest.parameters:
            if param.required and param.name not in params:
                return False, f"Missing required parameter: {param.name}"

        # Type checking
        for param in manifest.parameters:
            if param.name in params:
                value = params[param.name]
                if not self._check_type(value, param.type):
                    return False, f"Invalid type for {param.name}: expected {param.type}"

                # Check choices
                if param.choices and value not in param.choices:
                    return False, f"Invalid value for {param.name}: must be one of {param.choices}"

        return True, None

    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type."""
        type_checks = {
            "string": lambda v: isinstance(v, str),
            "str": lambda v: isinstance(v, str),
            "int": lambda v: isinstance(v, int) and not isinstance(v, bool),
            "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
            "float": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
            "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
            "bool": lambda v: isinstance(v, bool),
            "boolean": lambda v: isinstance(v, bool),
            "list": lambda v: isinstance(v, list),
            "array": lambda v: isinstance(v, list),
            "dict": lambda v: isinstance(v, dict),
            "object": lambda v: isinstance(v, dict),
        }

        checker = type_checks.get(expected_type.lower())
        if checker:
            return checker(value)
        return True  # Unknown types pass

    @property
    def name(self) -> str:
        """Get tool name."""
        return self.manifest.name

    @property
    def description(self) -> str:
        """Get tool description."""
        return self.manifest.description

    def get_schema(self) -> dict:
        """Get JSON schema for this tool."""
        return self.manifest.to_schema()

