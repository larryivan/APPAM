import json
from typing import List, Dict, Any, Optional
from .base import BaseTool, ToolResult

class ToolRegistry:
    """A registry to discover, store, and execute tools."""

    def __init__(self, tools: List[BaseTool] = None):
        self._tools: Dict[str, BaseTool] = {}
        if tools:
            for tool in tools:
                self.register_tool(tool)

    def register_tool(self, tool: BaseTool):
        """Registers a single tool."""
        if tool.name in self._tools:
            print(f"Warning: Tool '{tool.name}' is already registered. Overwriting.")
        self._tools[tool.name] = tool

    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Retrieves a tool by its name."""
        return self._tools.get(tool_name)

    def get_all_tools(self) -> List[BaseTool]:
        """Returns a list of all registered tools."""
        return list(self._tools.values())

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Returns the OpenAI-compatible definitions for all registered tools."""
        return [tool.get_definition() for tool in self._tools.values()]

    def execute_tool(self, tool_name: str, arguments: str) -> ToolResult:
        """
        Executes a tool by its name with the given JSON string of arguments.
        """
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolResult(is_success=False, content=f"Error: Tool '{tool_name}' not found.")

        try:
            args_dict = json.loads(arguments)
            return tool.execute(**args_dict)
        except json.JSONDecodeError:
            return ToolResult(is_success=False, content=f"Error: Invalid JSON arguments for tool '{tool_name}'.")
        except Exception as e:
            # This will catch errors during tool.execute() if the tool itself fails to handle them.
            return ToolResult(
                is_success=False,
                content=f"An unexpected error occurred while executing tool '{tool_name}': {e}",
                error_details=str(e)
            ) 