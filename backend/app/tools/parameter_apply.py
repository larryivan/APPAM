"""
Parameter apply tool for sending parameter suggestions to the frontend form.
"""

import json
from typing import Dict, List, Optional, Any
from .base import BaseTool, ToolResult


class ParameterApplyTool(BaseTool):
    """Tool for applying parameter suggestions to frontend form."""
    
    def __init__(self):
        super().__init__()
    
    @property
    def name(self) -> str:
        return "apply_parameters"
    
    @property
    def description(self) -> str:
        return "Apply parameter suggestions to the frontend form"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tool_name": {
                    "type": "string",
                    "description": "Name of the tool to apply parameters for"
                },
                "parameters": {
                    "type": "object",
                    "description": "Parameter values to apply to the form"
                },
                "summary": {
                    "type": "string",
                    "description": "Summary of the parameter changes"
                }
            },
            "required": ["tool_name", "parameters"]
        }
    
    def execute(self, tool_name: str, parameters: Dict, summary: Optional[str] = None) -> ToolResult:
        """Execute parameter application."""
        
        # Prepare the result that will be sent to frontend
        result_metadata = {
            "tool_name": tool_name,
            "parameters": parameters,
            "summary": summary or f"Applied parameters for {tool_name}",
            "action": "apply_parameters"
        }
        
        # Create a user-friendly message
        param_list = []
        for param_name, param_value in parameters.items():
            param_list.append(f"• {param_name}: {param_value}")
        
        content = f"已为{tool_name}应用以下参数:\n\n" + "\n".join(param_list)
        
        if summary:
            content += f"\n\n{summary}"
        
        return ToolResult(
            is_success=True,
            content=content,
            metadata=result_metadata
        ) 