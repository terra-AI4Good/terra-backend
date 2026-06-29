"""Base tool interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """Result returned by a tool execution."""

    success: bool = True
    data: Any = None
    error: str | None = None


class ToolParameter(BaseModel):
    """Schema for a single tool parameter."""

    name: str
    type: str = "string"
    description: str = ""
    required: bool = True
    enum: list[str] | None = None


class ToolDefinition(BaseModel):
    """Tool metadata — used to generate the OpenAI function-calling schema."""

    name: str
    description: str
    parameters: list[ToolParameter] = Field(default_factory=list)

    def to_openai_schema(self) -> dict[str, Any]:
        """Convert to OpenAI-compatible tool definition."""
        properties: dict[str, Any] = {}
        required: list[str] = []

        for param in self.parameters:
            prop: dict[str, Any] = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            properties[param.name] = prop
            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }


class Tool(ABC):
    """Abstract base class for all tools.

    Subclass this and implement `execute` to create a new tool.
    """

    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """Return the tool's metadata and parameter schema."""

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with the given arguments.

        Args:
            **kwargs: Tool-specific parameters matching the definition schema.

        Returns:
            ToolResult with the outcome.
        """

    @property
    def name(self) -> str:
        """Shortcut for the tool's registered name."""
        return self.definition.name

    def to_openai_schema(self) -> dict[str, Any]:
        """Generate the OpenAI function-calling schema for this tool."""
        return self.definition.to_openai_schema()
