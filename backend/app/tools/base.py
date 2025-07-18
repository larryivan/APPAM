from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class ToolResult(BaseModel):
    """Standardized result format for all tool executions."""
    is_success: bool = Field(..., description="Whether the tool execution was successful.")
    content: str = Field(..., description="The output of the tool. Can be a success message, data, or an error message.")
    error_details: Optional[str] = Field(None, description="Detailed error message if execution failed.")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata from tool execution.")

class BaseTool(ABC):
    """Abstract base class for all tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """A description of what the tool does."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """A dictionary describing the tool's parameters in OpenAI function calling format."""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Executes the tool with the given arguments."""
        pass

    def get_definition(self) -> Dict[str, Any]:
        """Returns the tool's definition in the format expected by OpenAI's API."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        } 